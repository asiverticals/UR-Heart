import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/sanctuary_http_client.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

class SuperadminKycDeskScreen extends ConsumerStatefulWidget {
  const SuperadminKycDeskScreen({super.key});

  @override
  ConsumerState<SuperadminKycDeskScreen> createState() => _SuperadminKycDeskScreenState();
}

class _SuperadminKycDeskScreenState extends ConsumerState<SuperadminKycDeskScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  List<Map<String, dynamic>> _escalations = [];
  int _currentIndex = 0;
  bool _isAdjudicating = false;

  @override
  void initState() {
    super.initState();
    _fetchEscalations();
  }

  Future<void> _fetchEscalations() async {
    if (_isAdjudicating) return;
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final client = ref.read(sanctuaryHttpClientProvider);
      final response = await client.get('/api/v1/admin/kyc/escalations');
      final rawData = response['data'];
      final List<Map<String, dynamic>> parsedList = [];
      if (rawData is List) {
        for (final item in rawData) {
          if (item is Map<String, dynamic>) {
            parsedList.add(item);
          }
        }
      }

      if (!mounted) return;
      setState(() {
        _escalations = parsedList;
        _isLoading = false;
        if (_currentIndex >= parsedList.length && parsedList.isNotEmpty) {
          _currentIndex = parsedList.length - 1;
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _adjudicateCurrent(String decision) async {
    if (_escalations.isEmpty || _currentIndex >= _escalations.length) return;
    final item = _escalations[_currentIndex];
    final escalationId = item['id']?.toString() ?? '';

    setState(() {
      _isAdjudicating = true;
    });

    try {
      final client = ref.read(sanctuaryHttpClientProvider);
      await client.post(
        '/api/v1/admin/kyc/$escalationId/decide',
        body: {'decision': decision, 'reviewer_notes': 'Manual adjudication via Superadmin KYC Desk'},
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              decision == 'approve'
                  ? 'Sacred Liveness affirmed for ${item['full_name']}.'
                  : 'Dossier rejected for ${item['full_name']}. Biometric purged.',
            ),
            backgroundColor: decision == 'approve'
                ? SanctuaryGlassTokens.onlineEmerald
                : SanctuaryGlassTokens.alertRed,
          ),
        );
      }

      if (!mounted) return;
      setState(() {
        _escalations.removeWhere((e) => e['id']?.toString() == escalationId);
        if (_currentIndex >= _escalations.length && _escalations.isNotEmpty) {
          _currentIndex = _escalations.length - 1;
        }
        _isAdjudicating = false;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Adjudication failed: $e'),
            backgroundColor: SanctuaryGlassTokens.alertRed,
          ),
        );
      }
      if (!mounted) return;
      setState(() {
        _isAdjudicating = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final tokens = SanctuaryGlassTokens.dark();

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Row(
          children: [
            const Text(
              'Sanctuary KYC Desk',
              style: TextStyle(
                fontFamily: 'PlayfairDisplay',
                fontSize: 20,
                fontWeight: FontWeight.w600,
                color: Color(0xFFFDFDFD),
              ),
            ),
            const SizedBox(width: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.5)),
              ),
              child: Text(
                '${_escalations.length} Pending',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: SanctuaryGlassTokens.brandSacredGold,
                ),
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
            onPressed: _isLoading ? null : _fetchEscalations,
          ),
        ],
      ),
      body: _buildBody(tokens),
    );
  }

  Widget _buildBody(SanctuaryGlassTokens tokens) {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(SanctuaryGlassTokens.brandSacredGold),
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: SanctuaryGlassContainer(
            blurSigma: 16.0,
            borderRadius: 16.0,
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.error_outline, color: SanctuaryGlassTokens.alertRed, size: 48),
                const SizedBox(height: 16),
                Text(
                  _errorMessage!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white70),
                ),
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  onPressed: _fetchEscalations,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry Connection'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    if (_escalations.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: SanctuaryGlassContainer(
            blurSigma: 16.0,
            borderRadius: 20.0,
            padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 40),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.verified_user_rounded, color: SanctuaryGlassTokens.onlineEmerald.withValues(alpha: 0.9), size: 56),
                const SizedBox(height: 20),
                const Text(
                  'Sanctuary Integrity Intact',
                  style: TextStyle(
                    fontFamily: 'PlayfairDisplay',
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'All seeker dossiers adjudicated. Sanctuary integrity intact.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 14, color: tokens.textSecondary, height: 1.4),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final item = _escalations[_currentIndex];
    final fullName = item['full_name']?.toString() ?? 'Seeker';
    final age = item['declared_age']?.toString() ?? 'Age unknown';
    final score = item['groq_match_score']?.toString() ?? '0.0';
    final anchorUrl = item['anchor_photo_url']?.toString() ?? '';
    final liveUrl = item['live_frame_url']?.toString() ?? '';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Meta Telemetry Chip
          SanctuaryGlassContainer(
            blurSigma: 16.0,
            borderRadius: 16.0,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '$fullName, $age',
                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                    const SizedBox(height: 4),
                    const Text('Declared Adult Seeker', style: TextStyle(fontSize: 12, color: Colors.white60)),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.4)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.bolt_rounded, size: 16, color: SanctuaryGlassTokens.brandSacredGold),
                      const SizedBox(width: 4),
                      Text(
                        'Groq Score: $score/100',
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: SanctuaryGlassTokens.brandSacredGold,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Side-by-Side Review Card
          SanctuaryGlassContainer(
            blurSigma: 16.0,
            borderRadius: 20.0,
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        children: [
                          const Text(
                            'Anchor Portrait',
                            style: TextStyle(fontWeight: FontWeight.w600, color: Colors.white70),
                          ),
                          const SizedBox(height: 8),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: AspectRatio(
                              aspectRatio: 3 / 4,
                              child: anchorUrl.isNotEmpty
                                  ? Image.network(
                                      anchorUrl,
                                      fit: BoxFit.cover,
                                      errorBuilder: (_, __, ___) => _buildPlaceholderPhoto('Portrait'),
                                    )
                                  : _buildPlaceholderPhoto('Portrait'),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        children: [
                          const Text(
                            'Live Capture Frame',
                            style: TextStyle(fontWeight: FontWeight.w600, color: Colors.white70),
                          ),
                          const SizedBox(height: 8),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: AspectRatio(
                              aspectRatio: 3 / 4,
                              child: liveUrl.isNotEmpty
                                  ? Image.network(
                                      liveUrl,
                                      fit: BoxFit.cover,
                                      errorBuilder: (_, __, ___) => _buildPlaceholderPhoto('Liveness Frame'),
                                    )
                                  : _buildPlaceholderPhoto('Liveness Frame'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Decision Controls
          if (_isAdjudicating)
            const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(SanctuaryGlassTokens.onlineEmerald),
              ),
            )
          else
            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.85),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    onPressed: () => _adjudicateCurrent('reject'),
                    icon: const Icon(Icons.close_rounded),
                    label: const Text('Reject Spoof / Mismatch'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: (anchorUrl.isNotEmpty && liveUrl.isNotEmpty)
                          ? SanctuaryGlassTokens.onlineEmerald.withValues(alpha: 0.85)
                          : Colors.white24,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    onPressed: (anchorUrl.isNotEmpty && liveUrl.isNotEmpty)
                        ? () => _adjudicateCurrent('approve')
                        : null,
                    icon: const Icon(Icons.check_rounded),
                    label: const Text('Affirm Sacred Liveness'),
                  ),
                ),
              ],
            ),
            if (anchorUrl.isEmpty || liveUrl.isEmpty)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Review images must be available before approval can be granted. Refresh to renew expired URLs.',
                  style: TextStyle(color: Colors.white60, fontSize: 12),
                  textAlign: TextAlign.center,
                ),
              ),
        ],
      ),
    );
  }

  Widget _buildPlaceholderPhoto(String label) {
    return Container(
      color: Colors.black26,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.photo_camera_back_outlined, color: Colors.white38, size: 36),
            const SizedBox(height: 6),
            Text(label, style: const TextStyle(fontSize: 12, color: Colors.white38)),
          ],
        ),
      ),
    );
  }
}
