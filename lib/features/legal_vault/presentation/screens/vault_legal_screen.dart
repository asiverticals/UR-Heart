import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../controllers/vault_controller.dart';

class VaultLegalScreen extends ConsumerStatefulWidget {
  final String? initialReportedUserId;

  const VaultLegalScreen({
    super.key,
    this.initialReportedUserId,
  });

  @override
  ConsumerState<VaultLegalScreen> createState() => _VaultLegalScreenState();
}

class _VaultLegalScreenState extends ConsumerState<VaultLegalScreen> {
  @override
  void initState() {
    super.initState();
    if (widget.initialReportedUserId != null && widget.initialReportedUserId!.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) {
          _showGrievanceModal(context, initialReportedUserId: widget.initialReportedUserId);
        }
      });
    }
  }
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();
    final state = ref.watch(vaultControllerProvider);

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: SafeArea(
        child: RefreshIndicator(
          color: SanctuaryGlassTokens.brandSacredGold,
          onRefresh: () => ref.read(vaultControllerProvider.notifier).loadVaultData(),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildTopBar(context, tokens, isDark),
                const SizedBox(height: 16.0),
                if (state.errorMessage != null) ...[
                  _buildMessageBanner(
                    message: state.errorMessage!,
                    isError: true,
                    tokens: tokens,
                  ),
                  const SizedBox(height: 12.0),
                ],
                if (state.successMessage != null) ...[
                  _buildMessageBanner(
                    message: state.successMessage!,
                    isError: false,
                    tokens: tokens,
                  ),
                  const SizedBox(height: 12.0),
                ],
                _buildNomineeSection(context, tokens, isDark, state),
                const SizedBox(height: 16.0),
                _buildGrievanceSection(context, tokens, isDark, state),
                const SizedBox(height: 16.0),
                _buildDataExportSection(context, tokens, isDark, state),
                const SizedBox(height: 32.0),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTopBar(BuildContext context, SanctuaryGlassTokens tokens, bool isDark) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            if (Navigator.canPop(context))
              IconButton(
                icon: Icon(Icons.arrow_back_ios_new, color: tokens.textPrimary, size: 20),
                onPressed: () => Navigator.of(context).pop(),
              ),
            Expanded(
              child: Text(
                'Sacred Legal Vault',
                style: TextStyle(
                  fontFamily: SanctuaryTypography.serifFont,
                  fontSize: 26.0,
                  fontWeight: FontWeight.w700,
                  color: tokens.textPrimary,
                  letterSpacing: -0.3,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4.0),
        Padding(
          padding: EdgeInsets.only(left: Navigator.canPop(context) ? 48.0 : 0.0),
          child: const Text(
            'Statutory Rights & DPDP Act 2023 Protections',
            style: TextStyle(
              fontSize: 12.0,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.5,
              color: SanctuaryGlassTokens.brandSacredGold,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildMessageBanner({
    required String message,
    required bool isError,
    required SanctuaryGlassTokens tokens,
  }) {
    final color = isError ? SanctuaryGlassTokens.alertRed : SanctuaryGlassTokens.onlineEmerald;
    return SanctuaryGlassContainer(
      padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 10.0),
      borderRadius: 12.0,
      customTint: color.withValues(alpha: 0.12),
      child: Row(
        children: [
          Icon(isError ? Icons.error_outline : Icons.check_circle_outline, color: color, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: tokens.textPrimary, fontSize: 13),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNomineeSection(
    BuildContext context,
    SanctuaryGlassTokens tokens,
    bool isDark,
    VaultState state,
  ) {
    final nominee = state.nominee;

    return SanctuaryGlassContainer(
      blurSigma: 16.0,
      borderRadius: 20.0,
      padding: const EdgeInsets.all(20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8.0),
                decoration: BoxDecoration(
                  color: SanctuaryGlassTokens.brandPine.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(10.0),
                ),
                child: const Icon(Icons.shield_outlined, color: SanctuaryGlassTokens.onlineEmerald, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Digital Nominee Designation',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.serifFont,
                        fontSize: 18.0,
                        fontWeight: FontWeight.w700,
                        color: tokens.textPrimary,
                      ),
                    ),
                    Text(
                      'Section 14 • DPDP Act 2023',
                      style: TextStyle(
                        fontSize: 11.0,
                        fontWeight: FontWeight.w600,
                        color: tokens.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12.0),
          Text(
            'Designate a trusted legal representative to exercise data rights, access account logs, or request complete account erasure in the event of incapacity or departure.',
            style: TextStyle(
              fontSize: 13.0,
              height: 1.4,
              color: tokens.textSecondary,
            ),
          ),
          const SizedBox(height: 16.0),
          if (nominee != null) ...[
            Container(
              padding: const EdgeInsets.all(14.0),
              decoration: BoxDecoration(
                color: tokens.glassTintSecondary,
                borderRadius: BorderRadius.circular(12.0),
                border: Border.all(
                  color: SanctuaryGlassTokens.onlineEmerald.withValues(alpha: 0.3),
                  width: 1.0,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          nominee.name,
                          style: TextStyle(
                            fontSize: 16.0,
                            fontWeight: FontWeight.w700,
                            color: tokens.textPrimary,
                          ),
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
                        decoration: BoxDecoration(
                          color: SanctuaryGlassTokens.onlineEmerald.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8.0),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.shield_outlined, color: SanctuaryGlassTokens.onlineEmerald, size: 14),
                            const SizedBox(width: 4),
                            Text(
                              nominee.verificationStatus.toUpperCase(),
                              style: const TextStyle(
                                fontSize: 11.0,
                                fontWeight: FontWeight.w600,
                                color: SanctuaryGlassTokens.onlineEmerald,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6.0),
                  Text(
                    '${nominee.relationship} • ${nominee.contact}',
                    style: TextStyle(fontSize: 13.0, color: tokens.textSecondary),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12.0),
            OutlinedButton(
              onPressed: () => _showNomineeModal(context, nominee: nominee),
              style: OutlinedButton.styleFrom(
                foregroundColor: tokens.textPrimary,
                side: BorderSide(color: tokens.borderSpecularStart),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12.0)),
                padding: const EdgeInsets.symmetric(vertical: 12.0),
              ),
              child: const Center(child: Text('Update Nominee Details')),
            ),
          ] else ...[
            Container(
              padding: const EdgeInsets.all(12.0),
              decoration: BoxDecoration(
                color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(10.0),
                border: Border.all(
                  color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.25),
                  width: 1.0,
                ),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline, color: SanctuaryGlassTokens.brandTerracotta, size: 18),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'No digital nominee appointed yet.',
                      style: TextStyle(fontSize: 12.0, color: SanctuaryGlassTokens.brandTerracotta),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12.0),
            ElevatedButton(
              onPressed: () => _showNomineeModal(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: SanctuaryGlassTokens.brandPine,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12.0)),
                padding: const EdgeInsets.symmetric(vertical: 12.0),
              ),
              child: const Center(child: Text('Designate Digital Nominee')),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildGrievanceSection(
    BuildContext context,
    SanctuaryGlassTokens tokens,
    bool isDark,
    VaultState state,
  ) {
    return SanctuaryGlassContainer(
      blurSigma: 16.0,
      borderRadius: 20.0,
      padding: const EdgeInsets.all(20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8.0),
                decoration: BoxDecoration(
                  color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(10.0),
                ),
                child: const Icon(Icons.gavel_outlined, color: SanctuaryGlassTokens.brandTerracotta, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Statutory Grievance Redressal',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.serifFont,
                        fontSize: 18.0,
                        fontWeight: FontWeight.w700,
                        color: tokens.textPrimary,
                      ),
                    ),
                    Text(
                      'Section 13 • IT Rules 2021 Rule 3(2) (15-Day SLA)',
                      style: TextStyle(
                        fontSize: 11.0,
                        fontWeight: FontWeight.w600,
                        color: tokens.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12.0),
          Text(
            'Every grievance submitted receives automated statutory acknowledgment within 24 hours with an immutable 15-calendar-day resolution SLA guaranteed by law.',
            style: TextStyle(
              fontSize: 13.0,
              height: 1.4,
              color: tokens.textSecondary,
            ),
          ),
          const SizedBox(height: 16.0),
          if (state.grievances.isEmpty) ...[
            Container(
              padding: const EdgeInsets.all(14.0),
              decoration: BoxDecoration(
                color: tokens.glassTintSecondary,
                borderRadius: BorderRadius.circular(12.0),
              ),
              child: Center(
                child: Text(
                  'No active grievances filed. Your sanctuary journey is serene and unblemished.',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12.5, color: tokens.textTertiary),
                ),
              ),
            ),
          ] else ...[
            ...state.grievances.map((g) => _buildGrievanceTile(context, g, tokens)),
          ],
          const SizedBox(height: 14.0),
          OutlinedButton(
            onPressed: () => _showGrievanceModal(context),
            style: OutlinedButton.styleFrom(
              foregroundColor: tokens.textPrimary,
              side: BorderSide(color: tokens.borderSpecularStart),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12.0)),
              padding: const EdgeInsets.symmetric(vertical: 12.0),
            ),
            child: const Center(child: Text('File Statutory Grievance')),
          ),
        ],
      ),
    );
  }

  Widget _buildGrievanceTile(
    BuildContext context,
    GrievanceDossierModel dossier,
    SanctuaryGlassTokens tokens,
  ) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10.0),
      padding: const EdgeInsets.all(12.0),
      decoration: BoxDecoration(
        color: tokens.glassTintSecondary,
        borderRadius: BorderRadius.circular(12.0),
        border: Border.all(color: tokens.borderSpecularEnd, width: 1.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  dossier.referenceId,
                  style: const TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 13.0,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.copy, size: 16),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                onPressed: () {
                  Clipboard.setData(ClipboardData(text: dossier.referenceId));
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Dossier reference copied')),
                  );
                },
              ),
            ],
          ),
          const SizedBox(height: 8.0),
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 3.0),
                decoration: BoxDecoration(
                  color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6.0),
                ),
                child: Text(
                  dossier.category.replaceAll('_', ' ').toUpperCase(),
                  style: const TextStyle(
                    fontSize: 10.0,
                    fontWeight: FontWeight.w700,
                    color: SanctuaryGlassTokens.brandTerracotta,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 3.0),
                decoration: BoxDecoration(
                  color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6.0),
                ),
                child: Text(
                  '${dossier.daysRemaining} days remaining',
                  style: const TextStyle(
                    fontSize: 10.0,
                    fontWeight: FontWeight.w700,
                    color: SanctuaryGlassTokens.brandSacredGold,
                  ),
                ),
              ),
              const Spacer(),
              Text(
                dossier.status.toUpperCase(),
                style: TextStyle(
                  fontSize: 11.0,
                  fontWeight: FontWeight.w600,
                  color: tokens.textSecondary,
                ),
              ),
            ],
          ),
          if (dossier.evidence.isNotEmpty) ...[
            const SizedBox(height: 8.0),
            Text(
              dossier.evidence,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 12.0, color: tokens.textTertiary),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDataExportSection(
    BuildContext context,
    SanctuaryGlassTokens tokens,
    bool isDark,
    VaultState state,
  ) {
    return SanctuaryGlassContainer(
      blurSigma: 16.0,
      borderRadius: 20.0,
      padding: const EdgeInsets.all(20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8.0),
                decoration: BoxDecoration(
                  color: SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(10.0),
                ),
                child: const Icon(Icons.file_download_outlined, color: SanctuaryGlassTokens.brandSacredGold, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Machine-Readable Data Portability',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.serifFont,
                        fontSize: 18.0,
                        fontWeight: FontWeight.w700,
                        color: tokens.textPrimary,
                      ),
                    ),
                    Text(
                      'Section 11 • Subject Access Request (SAR)',
                      style: TextStyle(
                        fontSize: 11.0,
                        fontWeight: FontWeight.w600,
                        color: tokens.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12.0),
          Text(
            'Request a full, portable JSON compilation of your profile attributes, verified photos, interaction logs, consent records, and store receipts. All cryptographic keys are permanently sanitized.',
            style: TextStyle(
              fontSize: 13.0,
              height: 1.4,
              color: tokens.textSecondary,
            ),
          ),
          const SizedBox(height: 16.0),
          ElevatedButton(
            onPressed: state.isExporting
                ? null
                : () async {
                    final exportData = await ref.read(vaultControllerProvider.notifier).requestDataExport();
                    if (exportData != null && context.mounted) {
                      _showExportDialog(context, exportData);
                    }
                  },
            style: ElevatedButton.styleFrom(
              backgroundColor: SanctuaryGlassTokens.brandSacredGold,
              foregroundColor: Colors.black,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12.0)),
              padding: const EdgeInsets.symmetric(vertical: 14.0),
            ),
            child: Center(
              child: state.isExporting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                    )
                  : const Text(
                      'Generate Full Data Export (JSON)',
                      style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14.0),
                    ),
            ),
          ),
        ],
      ),
    );
  }

  void _showNomineeModal(BuildContext context, {NomineeModel? nominee}) {
    final nameCtrl = TextEditingController(text: nominee?.name ?? '');
    final contactCtrl = TextEditingController(text: nominee?.contact ?? '');
    final relCtrl = TextEditingController(text: nominee?.relationship ?? '');

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final isDark = Theme.of(context).brightness == Brightness.dark;
        final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
          child: SanctuaryGlassContainer(
            borderRadius: 24.0,
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  nominee == null ? 'Designate Digital Nominee' : 'Update Digital Nominee',
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.serifFont,
                    fontSize: 20.0,
                    fontWeight: FontWeight.w700,
                    color: tokens.textPrimary,
                  ),
                ),
                const SizedBox(height: 16.0),
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Nominee Full Name',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12.0),
                TextField(
                  controller: contactCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Phone Number or Email',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12.0),
                TextField(
                  controller: relCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Relationship (e.g. Sister, Spouse, Mother)',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 20.0),
                ElevatedButton(
                  onPressed: () async {
                    final name = nameCtrl.text.trim();
                    final contact = contactCtrl.text.trim();
                    final rel = relCtrl.text.trim();
                    if (name.length < 2 || contact.length < 5 || rel.length < 2) {
                      return;
                    }
                    Navigator.of(ctx).pop();
                    await ref.read(vaultControllerProvider.notifier).saveNominee(
                          name: name,
                          contact: contact,
                          relationship: rel,
                        );
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: SanctuaryGlassTokens.brandPine,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12.0)),
                    padding: const EdgeInsets.symmetric(vertical: 14.0),
                  ),
                  child: const Text('Seal Nominee into Vault'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  void _showGrievanceModal(BuildContext context, {String? initialReportedUserId}) {
    final userCtrl = TextEditingController(text: initialReportedUserId ?? '');
    final evidenceCtrl = TextEditingController();
    String category = 'harassment';

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final isDark = Theme.of(context).brightness == Brightness.dark;
        final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

        return StatefulBuilder(
          builder: (context, setModalState) {
            return Padding(
              padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
              child: SanctuaryGlassContainer(
                borderRadius: 24.0,
                padding: const EdgeInsets.all(24.0),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'File Statutory Grievance',
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.serifFont,
                        fontSize: 20.0,
                        fontWeight: FontWeight.w700,
                        color: tokens.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 16.0),
                    TextField(
                      controller: userCtrl,
                      decoration: const InputDecoration(
                        labelText: 'Reported User UUID',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12.0),
                    DropdownButtonFormField<String>(
                      initialValue: category,
                      decoration: const InputDecoration(
                        labelText: 'Violation Category',
                        border: OutlineInputBorder(),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'harassment', child: Text('Harassment')),
                        DropdownMenuItem(value: 'explicit_content', child: Text('Explicit Content')),
                        DropdownMenuItem(value: 'impersonation', child: Text('Impersonation')),
                        DropdownMenuItem(value: 'underage', child: Text('Underage Account')),
                        DropdownMenuItem(value: 'offplatform_leak', child: Text('Off-platform Leak')),
                      ],
                      onChanged: (val) {
                        if (val != null) {
                          setModalState(() => category = val);
                        }
                      },
                    ),
                    const SizedBox(height: 12.0),
                    TextField(
                      controller: evidenceCtrl,
                      maxLines: 3,
                      decoration: const InputDecoration(
                        labelText: 'Context & Evidence Narrative',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 20.0),
                    ElevatedButton(
                      onPressed: () async {
                        final reportedId = userCtrl.text.trim();
                        final evidence = evidenceCtrl.text.trim();
                        if (reportedId.isEmpty) return;
                        Navigator.of(ctx).pop();
                        await ref.read(vaultControllerProvider.notifier).submitGrievance(
                              reportedUserId: reportedId,
                              category: category,
                              evidence: evidence,
                            );
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: SanctuaryGlassTokens.brandTerracotta,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12.0)),
                        padding: const EdgeInsets.symmetric(vertical: 14.0),
                      ),
                      child: const Text('Submit Statutory Dossier (15-Day SLA)'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _showExportDialog(BuildContext context, Map<String, dynamic> exportData) {
    showDialog(
      context: context,
      builder: (ctx) {
        final prettyJson = const JsonEncoder.withIndent('  ').convert(exportData);
        return AlertDialog(
          title: const Text('Data Portability Archive Ready'),
          content: SizedBox(
            width: double.maxFinite,
            height: 300,
            child: SingleChildScrollView(
              child: SelectableText(
                prettyJson,
                style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Clipboard.setData(ClipboardData(text: prettyJson));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Export JSON copied to clipboard')),
                );
              },
              child: const Text('Copy JSON'),
            ),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Close'),
            ),
          ],
        );
      },
    );
  }
}
