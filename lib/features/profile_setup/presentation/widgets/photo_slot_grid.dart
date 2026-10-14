import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../controllers/profile_setup_controller.dart';

/// 5-slot interactive photo grid mapped directly to Cloudflare R2 moments.
/// Slot 1 functions as the Primary Hero Avatar, while slots 2–5 form the moment grid.
class PhotoSlotGrid extends ConsumerWidget {
  final Future<List<int>?> Function(int slot)? onPickImage;

  const PhotoSlotGrid({
    super.key,
    this.onPickImage,
  });

  Future<void> _onSlotTapped(BuildContext context, WidgetRef ref, int slotIndex) async {
    if (onPickImage == null) return;
    final bytes = await onPickImage!(slotIndex);
    if (bytes != null && bytes.isNotEmpty) {
      await ref.read(profileSetupControllerProvider.notifier).uploadPhotoSlot(slotIndex, bytes);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(profileSetupControllerProvider);
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section Header
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Sacred Moments (5 Slots)',
              style: TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: tokens.textPrimary,
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
              ),
              child: Text(
                '${state.photoUrls.where((p) => p != null).length}/5 Uploaded',
                style: const TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: SanctuaryGlassTokens.brandSacredGold,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Hero Slot 1 (Primary Persona Avatar)
        _buildHeroSlot(
          context: context,
          ref: ref,
          tokens: tokens,
          isDark: isDark,
          url: state.photoUrls[0],
          isUploading: state.isUploadingMedia,
          progress: state.uploadProgress,
        ),
        const SizedBox(height: 12),

        // 2x2 Grid for Slots 2, 3, 4, 5
        Row(
          children: [
            Expanded(
              child: _buildSecondarySlot(
                context: context,
                ref: ref,
                tokens: tokens,
                isDark: isDark,
                slotIndex: 2,
                url: state.photoUrls[1],
                isUploading: state.isUploadingMedia,
                progress: state.uploadProgress,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildSecondarySlot(
                context: context,
                ref: ref,
                tokens: tokens,
                isDark: isDark,
                slotIndex: 3,
                url: state.photoUrls[2],
                isUploading: state.isUploadingMedia,
                progress: state.uploadProgress,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildSecondarySlot(
                context: context,
                ref: ref,
                tokens: tokens,
                isDark: isDark,
                slotIndex: 4,
                url: state.photoUrls[3],
                isUploading: state.isUploadingMedia,
                progress: state.uploadProgress,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _buildSecondarySlot(
                context: context,
                ref: ref,
                tokens: tokens,
                isDark: isDark,
                slotIndex: 5,
                url: state.photoUrls[4],
                isUploading: state.isUploadingMedia,
                progress: state.uploadProgress,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildHeroSlot({
    required BuildContext context,
    required WidgetRef ref,
    required SanctuaryGlassTokens tokens,
    required bool isDark,
    required String? url,
    required bool isUploading,
    required double progress,
  }) {
    return SanctuaryGlassContainer(
      height: 210,
      width: double.infinity,
      borderRadius: 18,
      padding: EdgeInsets.zero,
      blurSigma: 16.0,
      onTap: isUploading ? null : () => _onSlotTapped(context, ref, 1),
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (url != null)
            Image.network(
              url,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => _buildPlaceholder(
                tokens: tokens,
                title: 'Slot 1 — Primary Avatar',
                subtitle: 'Tap to replace hero photo',
              ),
            )
          else
            _buildPlaceholder(
              tokens: tokens,
              title: 'Slot 1 — Primary Avatar',
              subtitle: 'Your principal persona image in discovery deck',
            ),

          // Primary Avatar Pill Badge
          Positioned(
            top: 12,
            left: 12,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                color: Colors.black.withValues(alpha: 0.55),
                border: Border.all(
                  color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.6),
                ),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.star_rounded,
                    size: 14,
                    color: SanctuaryGlassTokens.brandSacredGold,
                  ),
                  SizedBox(width: 4),
                  Text(
                    'Primary Avatar',
                    style: TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: SanctuaryGlassTokens.brandSacredGold,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Delete Button (if populated)
          if (url != null && !isUploading)
            Positioned(
              top: 10,
              right: 10,
              child: GestureDetector(
                onTap: () => ref.read(profileSetupControllerProvider.notifier).removePhotoSlot(1),
                child: Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.black.withValues(alpha: 0.65),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.3)),
                  ),
                  child: const Icon(Icons.close_rounded, size: 18, color: Colors.white),
                ),
              ),
            ),

          // Uploading Spinner Overlay
          if (isUploading && url == null)
            Container(
              color: Colors.black.withValues(alpha: 0.4),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const CircularProgressIndicator(
                      strokeWidth: 3,
                      valueColor: AlwaysStoppedAnimation(SanctuaryGlassTokens.brandSacredGold),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Uploading to R2... ${(progress * 100).toInt()}%',
                      style: const TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 12,
                        color: Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSecondarySlot({
    required BuildContext context,
    required WidgetRef ref,
    required SanctuaryGlassTokens tokens,
    required bool isDark,
    required int slotIndex,
    required String? url,
    required bool isUploading,
    required double progress,
  }) {
    return SanctuaryGlassContainer(
      height: 130,
      borderRadius: 14,
      padding: EdgeInsets.zero,
      blurSigma: 12.0,
      onTap: isUploading ? null : () => _onSlotTapped(context, ref, slotIndex),
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (url != null)
            Image.network(
              url,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => _buildSmallPlaceholder(tokens, slotIndex),
            )
          else
            _buildSmallPlaceholder(tokens, slotIndex),

          // Delete Button
          if (url != null && !isUploading)
            Positioned(
              top: 6,
              right: 6,
              child: GestureDetector(
                onTap: () => ref.read(profileSetupControllerProvider.notifier).removePhotoSlot(slotIndex),
                child: Container(
                  width: 26,
                  height: 26,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.black.withValues(alpha: 0.65),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.3)),
                  ),
                  child: const Icon(Icons.close_rounded, size: 14, color: Colors.white),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildPlaceholder({
    required SanctuaryGlassTokens tokens,
    required String title,
    required String subtitle,
  }) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.15),
            ),
            child: const Icon(
              Icons.add_photo_alternate_outlined,
              size: 28,
              color: SanctuaryGlassTokens.brandTerracotta,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            title,
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: tokens.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              fontSize: 11,
              color: tokens.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSmallPlaceholder(SanctuaryGlassTokens tokens, int slotIndex) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.add_photo_alternate_outlined,
            size: 22,
            color: SanctuaryGlassTokens.brandTerracotta,
          ),
          const SizedBox(height: 6),
          Text(
            'Slot $slotIndex',
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: tokens.textTertiary,
            ),
          ),
        ],
      ),
    );
  }
}
