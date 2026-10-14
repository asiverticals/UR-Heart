import 'package:flutter/material.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

class ClosureTemplateOption {
  final String key;
  final String text;
  final String title;

  const ClosureTemplateOption({
    required this.key,
    required this.title,
    required this.text,
  });
}

const List<ClosureTemplateOption> kClosureTemplates = [
  ClosureTemplateOption(
    key: 'grace_paths_diverge',
    title: 'Paths Diverge',
    text: 'Our paths diverge, but I honor our shared dialogue.',
  ),
  ClosureTemplateOption(
    key: 'grace_not_aligned',
    title: 'Differing Rhythms',
    text: 'I felt our core rhythms differ, wishing you clarity.',
  ),
  ClosureTemplateOption(
    key: 'grace_holding_space',
    title: 'Quiet Solitude',
    text: 'Taking time for quiet solitude; bowing out with gratitude.',
  ),
];

/// Tier 3 Modal Glass dialog replacing abrupt ghosting with mindful closure.
class PassWithGraceDialog extends StatefulWidget {
  final Future<bool> Function(String templateKey, String? note) onConfirmClosure;

  const PassWithGraceDialog({
    super.key,
    required this.onConfirmClosure,
  });

  static Future<bool?> show(
    BuildContext context, {
    required Future<bool> Function(String templateKey, String? note) onConfirmClosure,
  }) {
    return showDialog<bool>(
      context: context,
      barrierDismissible: true,
      barrierColor: Colors.black.withValues(alpha: 0.65),
      builder: (ctx) => PassWithGraceDialog(onConfirmClosure: onConfirmClosure),
    );
  }

  @override
  State<PassWithGraceDialog> createState() => _PassWithGraceDialogState();
}

class _PassWithGraceDialogState extends State<PassWithGraceDialog> {
  String _selectedTemplateKey = 'grace_paths_diverge';
  final TextEditingController _noteController = TextEditingController();
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _handleConfirm() async {
    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    final note = _noteController.text.trim();
    final success = await widget.onConfirmClosure(
      _selectedTemplateKey,
      note.isNotEmpty ? note : null,
    );

    if (!mounted) return;

    if (success) {
      Navigator.of(context).pop(true);
    } else {
      setState(() {
        _isSubmitting = false;
        _errorMessage = 'Could not conclude dialogue. Please try again.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
        child: Material(
          color: Colors.transparent,
          child: SanctuaryGlassContainer(
            borderRadius: 24.0,
            blurSigma: 24.0, // Tier 3 Modal Glass
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header Icon
                Center(
                  child: Container(
                    padding: const EdgeInsets.all(12.0),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: SanctuaryGlassTokens.brandPine.withValues(alpha: 0.15),
                      border: Border.all(
                        color: SanctuaryGlassTokens.brandPine.withValues(alpha: 0.4),
                        width: 1.0,
                      ),
                    ),
                    child: const Icon(
                      Icons.spa_outlined,
                      size: 28.0,
                      color: SanctuaryGlassTokens.brandPine,
                    ),
                  ),
                ),
                const SizedBox(height: 16.0),

                // Title
                Text(
                  'Part Ways with Grace',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.serifFont,
                    fontSize: 20.0,
                    fontWeight: FontWeight.w700,
                    color: tokens.textPrimary,
                  ),
                ),
                const SizedBox(height: 8.0),

                // Subtitle
                Text(
                  'Ghosting shocks the spirit. Select a mindful closure thought to conclude this kinship with dignity.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 13.0,
                    height: 1.4,
                    color: tokens.textSecondary,
                  ),
                ),
                const SizedBox(height: 20.0),

                // 3 Curated Selection Tiles
                ...kClosureTemplates.map((template) {
                  final isSelected = _selectedTemplateKey == template.key;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 10.0),
                    child: InkWell(
                      onTap: () {
                        setState(() {
                          _selectedTemplateKey = template.key;
                        });
                      },
                      borderRadius: BorderRadius.circular(14.0),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.all(14.0),
                        decoration: BoxDecoration(
                          color: isSelected
                              ? SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.12)
                              : tokens.glassTintSecondary,
                          borderRadius: BorderRadius.circular(14.0),
                          border: Border.all(
                            color: isSelected
                                ? SanctuaryGlassTokens.brandTerracotta
                                : tokens.borderSpecularStart.withValues(alpha: 0.2),
                            width: isSelected ? 1.5 : 1.0,
                          ),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              isSelected
                                  ? Icons.radio_button_checked
                                  : Icons.radio_button_unchecked,
                              size: 18.0,
                              color: isSelected
                                  ? SanctuaryGlassTokens.brandTerracotta
                                  : tokens.textTertiary,
                            ),
                            const SizedBox(width: 12.0),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    template.title,
                                    style: TextStyle(
                                      fontFamily: SanctuaryTypography.sansFont,
                                      fontSize: 13.5,
                                      fontWeight: FontWeight.w600,
                                      color: isSelected
                                          ? SanctuaryGlassTokens.brandTerracotta
                                          : tokens.textPrimary,
                                    ),
                                  ),
                                  const SizedBox(height: 4.0),
                                  Text(
                                    '"${template.text}"',
                                    style: TextStyle(
                                      fontFamily: SanctuaryTypography.serifFont,
                                      fontStyle: FontStyle.italic,
                                      fontSize: 12.5,
                                      height: 1.35,
                                      color: tokens.textSecondary,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }),

                const SizedBox(height: 10.0),

                // Optional Farewell Note
                TextField(
                  controller: _noteController,
                  maxLength: 300,
                  maxLines: 2,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 13.0,
                    color: tokens.textPrimary,
                  ),
                  decoration: InputDecoration(
                    counterText: '',
                    hintText: 'Optional farewell reflection (modest & kind)...',
                    hintStyle: TextStyle(
                      fontFamily: SanctuaryTypography.sansFont,
                      fontSize: 12.5,
                      color: tokens.textTertiary,
                    ),
                    filled: true,
                    fillColor: tokens.glassTintPrimary,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 10.0),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12.0),
                      borderSide: BorderSide(
                        color: tokens.borderSpecularStart.withValues(alpha: 0.3),
                      ),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12.0),
                      borderSide: BorderSide(
                        color: tokens.borderSpecularStart.withValues(alpha: 0.2),
                      ),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12.0),
                      borderSide: const BorderSide(
                        color: SanctuaryGlassTokens.brandPine,
                      ),
                    ),
                  ),
                ),

                if (_errorMessage != null) ...[
                  const SizedBox(height: 8.0),
                  Text(
                    _errorMessage!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: SanctuaryGlassTokens.alertRed,
                      fontSize: 12.0,
                    ),
                  ),
                ],

                const SizedBox(height: 16.0),

                // Action Buttons
                Row(
                  children: [
                    Expanded(
                      child: TextButton(
                        onPressed: _isSubmitting
                            ? null
                            : () => Navigator.of(context).pop(false),
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 12.0),
                        ),
                        child: Text(
                          'Remain in Dialogue',
                          style: TextStyle(
                            fontFamily: SanctuaryTypography.sansFont,
                            fontSize: 13.0,
                            color: tokens.textTertiary,
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12.0),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: _isSubmitting ? null : _handleConfirm,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: SanctuaryGlassTokens.brandTerracotta,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 12.0),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12.0),
                          ),
                          elevation: 0,
                        ),
                        child: _isSubmitting
                            ? const SizedBox(
                                height: 16.0,
                                width: 16.0,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2.0,
                                  color: Colors.white,
                                ),
                              )
                            : const Text(
                                'Pass with Grace',
                                style: TextStyle(
                                  fontFamily: SanctuaryTypography.sansFont,
                                  fontSize: 13.0,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
