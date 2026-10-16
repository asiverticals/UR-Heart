import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/constants/app_typography.dart';
import '../../../../core/network/sanctuary_http_client.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

/// Screen 2: ChatsListScreen (Main Bottom Nav Tab Index 2)
/// Displays active bilateral dialogues and match conversations.
class ChatsListScreen extends ConsumerStatefulWidget {
  const ChatsListScreen({super.key});

  @override
  ConsumerState<ChatsListScreen> createState() => _ChatsListScreenState();
}

class _ChatsListScreenState extends ConsumerState<ChatsListScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  List<Map<String, dynamic>> _matches = [];

  @override
  void initState() {
    super.initState();
    _fetchMatches();
  }

  Future<void> _fetchMatches() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final client = ref.read(sanctuaryHttpClientProvider);
      final res = await client.get('/api/v1/resonances/mutual');
      final rawData = res['data'];
      final List<Map<String, dynamic>> parsedList = [];

      if (rawData is List) {
        for (final item in rawData) {
          if (item is Map<String, dynamic>) {
            parsedList.add(item);
          } else if (item is Map) {
            parsedList.add(Map<String, dynamic>.from(item));
          }
        }
      }

      if (!mounted) return;
      setState(() {
        _matches = parsedList;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Header Bar
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Dialogues',
                        style: SanctuaryTypography.titleH1(tokens.textPrimary, isDark: isDark),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Sacred bilateral conversations',
                        style: SanctuaryTypography.caption(tokens.textSecondary),
                      ),
                    ],
                  ),
                  SanctuaryGlassContainer(
                    borderRadius: 20,
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.forum_outlined,
                          size: 16,
                          color: tokens.glowTerracotta,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          '${_matches.length}',
                          style: TextStyle(
                            fontFamily: SanctuaryTypography.sansFont,
                            fontWeight: FontWeight.w700,
                            fontSize: 13,
                            color: tokens.textPrimary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 8),

            // 2. Body List or State
            Expanded(
              child: RefreshIndicator(
                color: tokens.glowTerracotta,
                backgroundColor: tokens.elevatedSurface,
                onRefresh: _fetchMatches,
                child: _buildBody(tokens, isDark),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(SanctuaryGlassTokens tokens, bool isDark) {
    if (_isLoading) {
      return Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(tokens.glowTerracotta),
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.wifi_off_rounded, size: 48, color: tokens.textSecondary),
              const SizedBox(height: 16),
              Text(
                'Unable to load dialogues',
                style: SanctuaryTypography.bodyMedium(tokens.textPrimary),
              ),
              const SizedBox(height: 8),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: SanctuaryTypography.caption(tokens.textSecondary),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _fetchMatches,
                style: ElevatedButton.styleFrom(
                  backgroundColor: tokens.glowTerracotta,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (_matches.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          const SizedBox(height: 100),
          Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40.0),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 72,
                    height: 72,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: tokens.glowTerracotta.withValues(alpha: 0.15),
                    ),
                    child: Icon(
                      Icons.spa_outlined,
                      size: 36,
                      color: tokens.glowTerracotta,
                    ),
                  ),
                  const SizedBox(height: 24),
                  Text(
                    'No Dialogues Yet',
                    style: SanctuaryTypography.titleH2(tokens.textPrimary, isDark: isDark),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'When reciprocal resonance is discovered, your private sacred dialogue will open here.',
                    textAlign: TextAlign.center,
                    style: SanctuaryTypography.bodyStandard(tokens.textSecondary),
                  ),
                ],
              ),
            ),
          ),
        ],
      );
    }

    return ListView.separated(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
      itemCount: _matches.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, index) {
        final match = _matches[index];
        final matchId = match['match_id']?.toString() ?? '';
        final peerId = match['peer_id']?.toString() ?? '';
        final peerName = match['peer_name']?.toString() ?? 'Seeker';
        final peerAvatar = match['peer_avatar']?.toString();
        final closureStatus = match['closure_status']?.toString() ?? 'active';
        final isClosed = closureStatus == 'closed_with_grace';

        return SanctuaryGlassContainer(
          borderRadius: 16,
          padding: const EdgeInsets.all(12),
          onTap: () {
            context.push('/chat-dialogue?matchId=$matchId&peerId=$peerId');
          },
          child: Row(
            children: [
              // Avatar
              CircleAvatar(
                radius: 26,
                backgroundColor: tokens.glowTerracotta.withValues(alpha: 0.2),
                backgroundImage: (peerAvatar != null && peerAvatar.isNotEmpty)
                    ? NetworkImage(peerAvatar)
                    : null,
                child: (peerAvatar == null || peerAvatar.isEmpty)
                    ? Text(
                        peerName.isNotEmpty ? peerName[0].toUpperCase() : 'S',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color: tokens.textPrimary,
                        ),
                      )
                    : null,
              ),

              const SizedBox(width: 14),

              // Peer info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            peerName,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontFamily: SanctuaryTypography.sansFont,
                              fontWeight: FontWeight.w600,
                              fontSize: 16,
                              color: tokens.textPrimary,
                            ),
                          ),
                        ),
                        if (isClosed) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.amber.withValues(alpha: 0.2),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              'Closed',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: tokens.textSecondary,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      isClosed ? 'Dialogue ended with grace' : 'Tap to open sacred dialogue',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: SanctuaryTypography.caption(tokens.textSecondary),
                    ),
                  ],
                ),
              ),

              Icon(
                Icons.chevron_right_rounded,
                color: tokens.textTertiary,
                size: 22,
              ),
            ],
          ),
        );
      },
    );
  }
}
