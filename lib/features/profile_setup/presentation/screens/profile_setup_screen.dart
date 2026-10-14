import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../controllers/profile_setup_controller.dart';
import '../widgets/photo_slot_grid.dart';
import '../widgets/voice_spark_recorder_widget.dart';

/// Master ProfileSetupScreen for Phase 4 Chunk 4.2 onboarding.
/// Incorporates 5-slot photo grid, voice spark recorder, core identity fields,
/// values & bio prose with live counter, and sacred contact bridge setup.
class ProfileSetupScreen extends ConsumerStatefulWidget {
  final Future<List<int>?> Function(int slot)? onPickImage;
  final Future<List<int>?> Function(double duration)? onRecordAudio;

  const ProfileSetupScreen({
    super.key,
    this.onPickImage,
    this.onRecordAudio,
  });

  @override
  ConsumerState<ProfileSetupScreen> createState() => _ProfileSetupScreenState();
}

class _ProfileSetupScreenState extends ConsumerState<ProfileSetupScreen> {
  late final TextEditingController _nameController;
  late final TextEditingController _professionController;
  late final TextEditingController _educationController;
  late final TextEditingController _bioController;
  late final TextEditingController _contactBridgeController;

  static const List<String> _genderOptions = ['Woman', 'Man', 'Non-Binary', 'Other'];
  static const List<String> _interestedInOptions = ['Men', 'Women', 'Everyone'];
  static const List<Map<String, String>> _contactBridgeOptions = [
    {'type': 'whatsapp', 'label': 'WhatsApp', 'prefix': '+91'},
    {'type': 'instagram', 'label': 'Instagram', 'prefix': '@'},
    {'type': 'telegram', 'label': 'Telegram', 'prefix': '@'},
    {'type': 'signal', 'label': 'Signal', 'prefix': '+'},
    {'type': 'snapchat', 'label': 'Snapchat', 'prefix': '@'},
  ];

  @override
  void initState() {
    super.initState();
    final initialState = ref.read(profileSetupControllerProvider);
    _nameController = TextEditingController(text: initialState.fullName);
    _professionController = TextEditingController(text: initialState.profession);
    _educationController = TextEditingController(text: initialState.education);
    _bioController = TextEditingController(text: initialState.bio);
    _contactBridgeController = TextEditingController(text: initialState.contactBridgeHandle);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _professionController.dispose();
    _educationController.dispose();
    _bioController.dispose();
    _contactBridgeController.dispose();
    super.dispose();
  }

  void _onEvaPolishSuggestion() {
    const polishedSample =
        'Seeker of conscious dialogue and stillness. Passionate about philosophy, sacred architecture, and mindful living. Intentional connections over algorithmic noise.';
    _bioController.text = polishedSample;
    ref.read(profileSetupControllerProvider.notifier).updateTextFields(bio: polishedSample);
  }

  Future<void> _submitProfile() async {
    final controller = ref.read(profileSetupControllerProvider.notifier);
    controller.updateTextFields(
      fullName: _nameController.text,
      profession: _professionController.text,
      education: _educationController.text,
      bio: _bioController.text,
      contactBridgeHandle: _contactBridgeController.text,
    );

    final success = await controller.submitProfile();
    if (success && mounted) {
      context.go('/main');
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(profileSetupControllerProvider);
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isDark
                ? [
                    const Color(0xFF0F1115),
                    const Color(0xFF141923),
                    const Color(0xFF0F1115),
                  ]
                : [
                    const Color(0xFFF9F6F0),
                    const Color(0xFFF0EBE1),
                    const Color(0xFFF9F6F0),
                  ],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top Header
                Center(
                  child: Column(
                    children: [
                      Text(
                        'Craft Your Sacred Persona',
                        style: TextStyle(
                          fontFamily: SanctuaryTypography.serifFont,
                          fontSize: 26,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.3,
                          color: tokens.textPrimary,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Conscious presence begins with authenticity.',
                        style: TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontSize: 13,
                          color: tokens.textSecondary,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // Section 1: 5-Slot Photo Grid
                PhotoSlotGrid(onPickImage: widget.onPickImage),
                const SizedBox(height: 28),

                // Section 2: Core Details
                _buildSectionTitle('Core Details', tokens),
                const SizedBox(height: 12),
                _buildGlassInputField(
                  controller: _nameController,
                  tokens: tokens,
                  label: 'Full Name',
                  hint: 'e.g. Radhika Sharma',
                  icon: Icons.person_outline_rounded,
                  maxLength: 60,
                  onChanged: (val) => ref.read(profileSetupControllerProvider.notifier).updateTextFields(fullName: val),
                ),
                const SizedBox(height: 12),
                _buildGlassInputField(
                  controller: _professionController,
                  tokens: tokens,
                  label: 'Profession / Calling',
                  hint: 'e.g. Visual Architect, Meditator',
                  icon: Icons.work_outline_rounded,
                  maxLength: 80,
                  onChanged: (val) => ref.read(profileSetupControllerProvider.notifier).updateTextFields(profession: val),
                ),
                const SizedBox(height: 12),
                _buildGlassInputField(
                  controller: _educationController,
                  tokens: tokens,
                  label: 'Education / Discipline',
                  hint: 'e.g. Design Anthropology, NID',
                  icon: Icons.school_outlined,
                  maxLength: 100,
                  onChanged: (val) => ref.read(profileSetupControllerProvider.notifier).updateTextFields(education: val),
                ),
                const SizedBox(height: 28),

                // Section 3: Identity & Affinity
                _buildSectionTitle('Identity & Affinity', tokens),
                const SizedBox(height: 12),
                Text(
                  'My Gender',
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: tokens.textSecondary,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _genderOptions.map((g) {
                    final selected = state.gender == g;
                    return _buildSelectablePill(
                      label: g,
                      selected: selected,
                      tokens: tokens,
                      onTap: () => ref.read(profileSetupControllerProvider.notifier).setGender(g),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 16),
                Text(
                  'Interested In',
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: tokens.textSecondary,
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _interestedInOptions.map((i) {
                    final selected = state.interestedIn == i;
                    return _buildSelectablePill(
                      label: i,
                      selected: selected,
                      tokens: tokens,
                      onTap: () => ref.read(profileSetupControllerProvider.notifier).setInterestedIn(i),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 28),

                // Section 4: Values & Bio Prose
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildSectionTitle('Values & Bio Prose', tokens),
                    GestureDetector(
                      onTap: _onEvaPolishSuggestion,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(10),
                          color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
                        ),
                        child: const Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.auto_awesome, size: 14, color: SanctuaryGlassTokens.brandSacredGold),
                            SizedBox(width: 4),
                            Text(
                              'Eva Polish',
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
                  ],
                ),
                const SizedBox(height: 12),
                SanctuaryGlassContainer(
                  borderRadius: 16,
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    children: [
                      TextField(
                        controller: _bioController,
                        maxLines: 4,
                        maxLength: 500,
                        style: TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontSize: 13,
                          height: 1.45,
                          color: tokens.textPrimary,
                        ),
                        decoration: InputDecoration(
                          border: InputBorder.none,
                          hintText: 'Describe your rhythm, intentionality, and sacred path...',
                          hintStyle: TextStyle(
                            fontFamily: SanctuaryTypography.sansFont,
                            fontSize: 13,
                            color: tokens.textTertiary,
                          ),
                          counterText: '',
                        ),
                        onChanged: (val) => ref.read(profileSetupControllerProvider.notifier).updateTextFields(bio: val),
                      ),
                      Align(
                        alignment: Alignment.bottomRight,
                        child: Text(
                          '${state.bio.length}/500',
                          style: TextStyle(
                            fontFamily: SanctuaryTypography.sansFont,
                            fontSize: 11,
                            color: state.bio.length > 500 ? SanctuaryGlassTokens.alertRed : tokens.textTertiary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 28),

                // Section 5: Voice Spark Recorder
                VoiceSparkRecorderWidget(onRecordAudio: widget.onRecordAudio),
                const SizedBox(height: 28),

                // Section 6: Sacred Contact Bridge Setup
                _buildSectionTitle('Sacred Contact Bridge', tokens),
                const SizedBox(height: 6),
                Text(
                  'Bilateral communication channel encrypted until mutual connection lock.',
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 11,
                    color: tokens.textSecondary,
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _contactBridgeOptions.map((bridge) {
                    final selected = state.contactBridgeType == bridge['type'];
                    return _buildSelectablePill(
                      label: bridge['label']!,
                      selected: selected,
                      tokens: tokens,
                      onTap: () => ref.read(profileSetupControllerProvider.notifier).setContactBridgeType(bridge['type']!),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 12),
                _buildGlassInputField(
                  controller: _contactBridgeController,
                  tokens: tokens,
                  label: 'Handle or Verified Number',
                  hint: state.contactBridgeType == 'whatsapp' ? '+91 98765 43210' : '@username',
                  icon: Icons.lock_outline_rounded,
                  maxLength: 64,
                  onChanged: (val) => ref.read(profileSetupControllerProvider.notifier).updateTextFields(contactBridgeHandle: val),
                ),
                const SizedBox(height: 16),

                // Error Banner
                if (state.errorMessage != null) ...[
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.15),
                      border: Border.all(color: SanctuaryGlassTokens.alertRed.withValues(alpha: 0.4)),
                    ),
                    child: Text(
                      state.errorMessage!,
                      style: const TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 12,
                        color: SanctuaryGlassTokens.alertRed,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(height: 16),
                ],

                // CTA Button
                SanctuaryGlassContainer(
                  width: double.infinity,
                  height: 56,
                  borderRadius: 16,
                  blurSigma: 16.0,
                  customBorderGradient: const LinearGradient(
                    colors: [
                      SanctuaryGlassTokens.brandSacredGold,
                      SanctuaryGlassTokens.brandTerracottaGlow,
                    ],
                  ),
                  customTint: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.18),
                  onTap: state.isSubmitting ? null : _submitProfile,
                  child: Center(
                    child: state.isSubmitting
                        ? const SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              valueColor: AlwaysStoppedAnimation(SanctuaryGlassTokens.brandSacredGold),
                            ),
                          )
                        : Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.auto_awesome,
                                size: 18,
                                color: SanctuaryGlassTokens.brandSacredGold,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                'Complete Profile & Enter Deck',
                                style: TextStyle(
                                  fontFamily: SanctuaryTypography.sansFont,
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                  letterSpacing: 0.2,
                                  color: tokens.textPrimary,
                                ),
                              ),
                            ],
                          ),
                  ),
                ),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title, SanctuaryGlassTokens tokens) {
    return Text(
      title,
      style: TextStyle(
        fontFamily: SanctuaryTypography.sansFont,
        fontSize: 15,
        fontWeight: FontWeight.w600,
        color: tokens.textPrimary,
      ),
    );
  }

  Widget _buildSelectablePill({
    required String label,
    required bool selected,
    required SanctuaryGlassTokens tokens,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: selected
              ? SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.2)
              : tokens.glassTintSecondary,
          border: Border.all(
            color: selected
                ? SanctuaryGlassTokens.brandSacredGold
                : tokens.textTertiary.withValues(alpha: 0.2),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontFamily: SanctuaryTypography.sansFont,
            fontSize: 12,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
            color: selected ? tokens.textPrimary : tokens.textSecondary,
          ),
        ),
      ),
    );
  }

  Widget _buildGlassInputField({
    required TextEditingController controller,
    required SanctuaryGlassTokens tokens,
    required String label,
    required String hint,
    required IconData icon,
    required int maxLength,
    required ValueChanged<String> onChanged,
  }) {
    return SanctuaryGlassContainer(
      borderRadius: 14,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 20, color: tokens.textTertiary),
          const SizedBox(width: 12),
          Expanded(
            child: TextField(
              controller: controller,
              maxLength: maxLength,
              style: TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 13,
                color: tokens.textPrimary,
              ),
              decoration: InputDecoration(
                border: InputBorder.none,
                labelText: label,
                labelStyle: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 12,
                  color: tokens.textSecondary,
                ),
                hintText: hint,
                hintStyle: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 12,
                  color: tokens.textTertiary,
                ),
                counterText: '',
              ),
              onChanged: onChanged,
            ),
          ),
        ],
      ),
    );
  }
}
