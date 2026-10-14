import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../controllers/profile_setup_controller.dart';

/// 7-Second Voice Spark recorder widget with visual waveform indicator.
/// Audio binary is capped strictly at 7.0 seconds and uploaded directly to Cloudflare R2.
class VoiceSparkRecorderWidget extends ConsumerStatefulWidget {
  final Future<List<int>?> Function(double duration)? onRecordAudio;

  const VoiceSparkRecorderWidget({
    super.key,
    this.onRecordAudio,
  });

  @override
  ConsumerState<VoiceSparkRecorderWidget> createState() => _VoiceSparkRecorderWidgetState();
}

class _VoiceSparkRecorderWidgetState extends ConsumerState<VoiceSparkRecorderWidget> {
  bool _isRecording = false;
  double _elapsedSeconds = 0.0;
  Timer? _timer;
  bool _hasRecordedClip = false;
  List<int>? _capturedAudioBytes;

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _startRecording() async {
    if (widget.onRecordAudio == null) return;
    setState(() {
      _isRecording = true;
      _elapsedSeconds = 0.0;
      _hasRecordedClip = false;
      _capturedAudioBytes = null;
    });

    _timer?.cancel();
    _timer = Timer.periodic(const Duration(milliseconds: 100), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() => _elapsedSeconds = (_elapsedSeconds + 0.1).clamp(0.0, 7.0));
      if (_elapsedSeconds >= 7.0) {
        _stopRecording();
      }
    });
  }

  Future<void> _stopRecording() async {
    _timer?.cancel();
    final clampedDuration = _elapsedSeconds.clamp(0.0, 7.0);
    setState(() {
      _isRecording = false;
      _elapsedSeconds = clampedDuration;
    });

    if (widget.onRecordAudio != null) {
      final bytes = await widget.onRecordAudio!(clampedDuration);
      if (mounted) {
        setState(() {
          _capturedAudioBytes = bytes;
          _hasRecordedClip = bytes != null && bytes.isNotEmpty;
        });
      }
    }
  }

  Future<void> _uploadVoiceSpark() async {
    if (_capturedAudioBytes == null || _capturedAudioBytes!.isEmpty) return;
    await ref
        .read(profileSetupControllerProvider.notifier)
        .uploadVoiceSpark(_capturedAudioBytes!, _elapsedSeconds);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(profileSetupControllerProvider);
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();
    final hasPreservedVoice = state.voiceSparkUrl != null;
    final isRecordingAvailable = widget.onRecordAudio != null;

    return SanctuaryGlassContainer(
      width: double.infinity,
      borderRadius: 18,
      blurSigma: 16.0,
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header Row
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: hasPreservedVoice
                      ? SanctuaryGlassTokens.onlineEmerald.withValues(alpha: 0.15)
                      : SanctuaryGlassTokens.brandPine.withValues(alpha: 0.15),
                ),
                child: Icon(
                  hasPreservedVoice ? Icons.check_circle_rounded : Icons.graphic_eq_rounded,
                  size: 20,
                  color: hasPreservedVoice
                      ? SanctuaryGlassTokens.onlineEmerald
                      : SanctuaryGlassTokens.brandPine,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '7-Second Voice Spark',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: tokens.textPrimary,
                      ),
                    ),
                    Text(
                      'A vocal resonance text cannot convey (7.0s max)',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 11,
                        color: tokens.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              // Timer Display
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(10),
                  color: _isRecording
                      ? SanctuaryGlassTokens.alertRed.withValues(alpha: 0.15)
                      : (isDark ? Colors.white.withValues(alpha: 0.08) : Colors.black.withValues(alpha: 0.06)),
                ),
                child: Text(
                  '${_elapsedSeconds.toStringAsFixed(1)}s / 7.0s',
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: _isRecording ? SanctuaryGlassTokens.alertRed : tokens.textPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Waveform Visualizer Simulation Bars
          SizedBox(
            height: 36,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: List.generate(24, (index) {
                final barHeight = 8.0 + (index % 5) * 5.0 + (_isRecording ? ((index * 3) % 12) : 0);
                final isActive = _isRecording && (index / 24.0) <= (_elapsedSeconds / 7.0);
                return Container(
                  width: 3.5,
                  height: barHeight,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(2),
                    color: isActive
                        ? SanctuaryGlassTokens.brandTerracottaGlow
                        : (hasPreservedVoice
                            ? SanctuaryGlassTokens.onlineEmerald.withValues(alpha: 0.6)
                            : tokens.textTertiary.withValues(alpha: 0.3)),
                  ),
                );
              }),
            ),
          ),
          const SizedBox(height: 16),

          // Action Controls
          Row(
            children: [
              // Record/Stop Circle Button
              GestureDetector(
                onTap: (!isRecordingAvailable || state.isUploadingMedia)
                    ? null
                    : () {
                        if (_isRecording) {
                          _stopRecording();
                        } else {
                          _startRecording();
                        }
                      },
                child: Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: !isRecordingAvailable
                        ? null
                        : LinearGradient(
                            colors: _isRecording
                                ? [SanctuaryGlassTokens.alertRed, const Color(0xFFB71C1C)]
                                : [SanctuaryGlassTokens.brandPine, const Color(0xFF1B4D3E)],
                          ),
                    color: !isRecordingAvailable
                        ? tokens.textTertiary.withValues(alpha: 0.15)
                        : null,
                    boxShadow: !isRecordingAvailable
                        ? null
                        : [
                            BoxShadow(
                              color: (_isRecording ? SanctuaryGlassTokens.alertRed : SanctuaryGlassTokens.brandPine)
                                  .withValues(alpha: 0.3),
                              blurRadius: 10,
                              spreadRadius: 1,
                            ),
                          ],
                  ),
                  child: Icon(
                    _isRecording ? Icons.stop_rounded : Icons.mic_none_rounded,
                    color: !isRecordingAvailable ? tokens.textTertiary : Colors.white,
                    size: 24,
                  ),
                ),
              ),
              const SizedBox(width: 14),

              // Status message or "Keep Voice Spark" trigger
              Expanded(
                child: _isRecording
                    ? const Text(
                        'Recording vocal essence... (auto-caps at 7s)',
                        style: TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontSize: 12,
                          color: SanctuaryGlassTokens.alertRed,
                          fontWeight: FontWeight.w500,
                        ),
                      )
                    : (_hasRecordedClip && !hasPreservedVoice)
                        ? ElevatedButton.icon(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: SanctuaryGlassTokens.brandSacredGold,
                              foregroundColor: Colors.black,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                            ),
                            onPressed: state.isUploadingMedia ? null : _uploadVoiceSpark,
                            icon: const Icon(Icons.cloud_upload_outlined, size: 18),
                            label: const Text(
                              'Keep Voice Spark',
                              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                          )
                        : Text(
                            hasPreservedVoice
                                ? 'Voice Spark Preserved on Edge CDN'
                                : (!isRecordingAvailable
                                    ? 'Voice recording unavailable'
                                    : 'Tap mic to capture 7-second voice intro'),
                            style: TextStyle(
                              fontFamily: SanctuaryTypography.sansFont,
                              fontSize: 12,
                              color: hasPreservedVoice
                                  ? SanctuaryGlassTokens.onlineEmerald
                                  : tokens.textSecondary,
                            ),
                          ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
