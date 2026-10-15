import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/sanctuary_http_client.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

class EvaPolishModal extends ConsumerStatefulWidget {
  final String rawBio;
  final String? profession;
  final String? education;
  final ValueChanged<String> onApply;

  const EvaPolishModal({
    super.key,
    required this.rawBio,
    this.profession,
    this.education,
    required this.onApply,
  });

  static Future<void> show({
    required BuildContext context,
    required String rawBio,
    String? profession,
    String? education,
    required ValueChanged<String> onApply,
  }) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => EvaPolishModal(
        rawBio: rawBio,
        profession: profession,
        education: education,
        onApply: onApply,
      ),
    );
  }

  @override
  ConsumerState<EvaPolishModal> createState() => _EvaPolishModalState();
}

class _EvaPolishModalState extends ConsumerState<EvaPolishModal> {
  bool _isLoading = true;
  bool _isFallback = false;
  bool _isTypewriterFinished = false;
  String _polishedBio = '';
  String _reflectionPrompt = '';
  String _displayedText = '';
  Timer? _typewriterTimer;

  @override
  void initState() {
    super.initState();
    _fetchPolish();
  }

  @override
  void dispose() {
    _typewriterTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchPolish() async {
    try {
      final client = ref.read(sanctuaryHttpClientProvider);
      final response = await client.post(
        '/api/v1/eva/polish-bio',
        body: {
          'raw_bio': widget.rawBio,
          'profession': widget.profession,
          'education': widget.education,
        },
      );

      final data = response['data'] as Map<String, dynamic>? ?? response;
      final polished = data['polished_bio']?.toString() ?? widget.rawBio;
      final prompt = data['reflection_prompt']?.toString() ??
          'What presence do you wish to invite into your sanctuary?';
      final engine = data['engine']?.toString() ?? '';
      final isFallback = engine == 'fallback' || engine.startsWith('offline');

      if (mounted) {
        setState(() {
          _polishedBio = polished;
          _reflectionPrompt = prompt;
          _isLoading = false;
          _isFallback = isFallback;
        });
        _startTypewriter(polished);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _polishedBio = widget.rawBio;
          _reflectionPrompt = 'Embrace your authentic voice.';
          _displayedText = widget.rawBio;
          _isLoading = false;
          _isFallback = true;
          _isTypewriterFinished = true;
        });
      }
    }
  }

  void _startTypewriter(String text) {
    int index = 0;
    _typewriterTimer?.cancel();
    setState(() {
      _isTypewriterFinished = false;
    });
    _typewriterTimer = Timer.periodic(const Duration(milliseconds: 22), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      if (index < text.length) {
        setState(() {
          _displayedText = text.substring(0, index + 1);
        });
        index++;
      } else {
        timer.cancel();
        if (mounted) {
          setState(() {
            _isTypewriterFinished = true;
          });
        }
      }
    });
  }

  void _skipTypewriter() {
    _typewriterTimer?.cancel();
    if (mounted) {
      setState(() {
        _displayedText = _polishedBio;
        _isTypewriterFinished = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        top: 24,
        left: 20,
        right: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      decoration: BoxDecoration(
        color: const Color(0xFF0F1115).withValues(alpha: 0.95),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        border: Border.all(
          color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.4),
          width: 1.2,
        ),
        boxShadow: [
          BoxShadow(
            color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.18),
            blurRadius: 32,
            spreadRadius: 4,
          ),
        ],
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Modal Handle
            Center(
              child: Container(
                width: 48,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 18),

            // Header with Sacred Reflection Icon
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.18),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.5),
                    ),
                  ),
                  child: const Icon(
                    Icons.auto_awesome,
                    color: SanctuaryGlassTokens.brandSacredGold,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Eva Sacred Reflection',
                      style: TextStyle(
                        fontFamily: 'PlayfairDisplay',
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Conscious, authentic refinement without fabrication',
                      style: TextStyle(fontSize: 12, color: Colors.white60),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 20),

            if (_isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 40.0),
                  child: Column(
                    children: [
                      CircularProgressIndicator(
                        valueColor: AlwaysStoppedAnimation<Color>(SanctuaryGlassTokens.brandSacredGold),
                      ),
                      SizedBox(height: 16),
                      Text(
                        'Eva is contemplating your authentic presence...',
                        style: TextStyle(fontSize: 13, color: Colors.white70),
                      ),
                    ],
                  ),
                ),
              )
            else ...[
              if (_isFallback)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  margin: const EdgeInsets.only(bottom: 14),
                  decoration: BoxDecoration(
                    color: Colors.amber.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: Colors.amber.withValues(alpha: 0.35),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline_rounded, color: Colors.amberAccent, size: 18),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'Eva service is operating in offline mode. Showing original draft.',
                          style: TextStyle(fontSize: 12, color: Colors.white70),
                        ),
                      ),
                      TextButton(
                        onPressed: () {
                          setState(() {
                            _isLoading = true;
                            _isFallback = false;
                          });
                          _fetchPolish();
                        },
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: const Text(
                          'Retry',
                          style: TextStyle(
                            fontSize: 12,
                            color: SanctuaryGlassTokens.brandSacredGold,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

              // Contemplation Prompt
              if (_reflectionPrompt.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.25),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.spa_rounded, color: SanctuaryGlassTokens.brandSacredGold, size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _reflectionPrompt,
                          style: const TextStyle(
                            fontSize: 13,
                            fontStyle: FontStyle.italic,
                            color: SanctuaryGlassTokens.brandSacredGold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

              // Side-by-Side (or stacked) Cards
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Original Draft Card
                  Expanded(
                    child: SanctuaryGlassContainer(
                      blurSigma: 16.0,
                      borderRadius: 16.0,
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.edit_note_rounded, size: 16, color: Colors.white60),
                              SizedBox(width: 6),
                              Text(
                                'Original Draft',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.white70,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Text(
                            widget.rawBio,
                            style: const TextStyle(
                              fontSize: 13,
                              color: Colors.white60,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Polished Prose Card (with Typewriter Effect & Tap-to-Reveal)
                  Expanded(
                    child: GestureDetector(
                      onTap: _skipTypewriter,
                      child: SanctuaryGlassContainer(
                        blurSigma: 24.0,
                        borderRadius: 16.0,
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Row(
                              children: [
                                Icon(Icons.auto_awesome_rounded, size: 16, color: SanctuaryGlassTokens.brandSacredGold),
                                SizedBox(width: 6),
                                Text(
                                  'Eva Polish',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: SanctuaryGlassTokens.brandSacredGold,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            Text(
                              _displayedText,
                              style: const TextStyle(
                                fontSize: 13,
                                color: Colors.white,
                                height: 1.4,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),

              // Action Buttons
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white70,
                        side: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      onPressed: () => Navigator.of(context).pop(),
                      child: const Text('Keep Original'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _isTypewriterFinished
                            ? SanctuaryGlassTokens.brandSacredGold
                            : SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.6),
                        foregroundColor: Colors.black,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      ),
                      onPressed: () {
                        if (!_isTypewriterFinished) {
                          _skipTypewriter();
                          return;
                        }
                        widget.onApply(_polishedBio.isNotEmpty ? _polishedBio : widget.rawBio);
                        Navigator.of(context).pop();
                      },
                      child: Text(
                        _isTypewriterFinished ? 'Apply Reflection' : 'Reveal Full Text',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
