1. Master Screen Inventory & Routing Map
UR-Heart Sanctuary implements 19 dedicated production screens alongside responsive shell containers for Condition C4 (Native Android + iOS/Desktop PWA parity). Every screen is rendered using the Living Frosted-Glass design tokens (SanctuaryGlassTokens), incorporating optical blur physics, specular gradients, and contrast shields.
MD

+ 1

┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        UR-HEART SANCTUARY SCREEN TOPOLOGY                              │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ CLUSTER A: Onboarding & Statutory Gates (Screens 1 – 4)                                │
│   • ConsentScreen (/consent)                 • AgeGateAuthScreen (/auth)               │
│   • MagicLinkScreen (/magic-link)            • ProfileSetupScreen (/profile-setup)     │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ CLUSTER B: Primary Navigation Shell & 5 Core Tabs (Screens 5 – 10)                     │
│   • SanctuaryNavigationShell (/main)         • FeedScreen (Tab 0: Discovery Deck)      │
│   • ResonancesScreen (Tab 1: Likes/Sparks)   • ChatsListScreen (Tab 2: Dialogues)      │
│   • GrowthHubScreen (Tab 3: Store & Ads)     • MyPersonaScreen (Tab 4: Seeker Persona) │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ CLUSTER C: Kinship Dialogue, Discovery Aux & Profiles (Screens 11 – 13)                │
│   • IgnoredProfilesScreen (/ignored-profiles)• ChatDialogueScreen (/chat-dialogue)     │
│   • SeekerProfileDetailScreen (/seeker-detail)                                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ CLUSTER D: Condition C1 Fast-Track Subsystem (Screens 14 – 15)                         │
│   • BlindDateHubScreen (/blind-date)         • BlindDateSessionScreen (/blind-date-...) │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ CLUSTER E: AI Companion, Statutory Vault & Governance (Screens 16 – 19)                │
│   • EvaSanctuaryScreen (/eva-sanctuary)      • VaultLegalScreen (/vault)               │
│   • SanctuarySettingsScreen (/settings)      • SuperadminKycDeskScreen (/admin/kyc-desk)│
│   • SanctuaryAppInfoScreen (/app-info)                                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘

MD

Master Screen Specification Table

# Screen Class Route Path File Location Glass Tier Riverpod Controller Binding

1 ConsentScreen /consent lib/features/auth/presentation/screens/consent_screen.dart Tier 1 (Standard) 
themeProvider, authStateProvider

MD

2 AgeGateAuthScreen /auth lib/features/auth/presentation/screens/age_gate_auth_screen.dart Tier 1 (Standard) 
authStateProvider

MD

3 MagicLinkScreen /magic-link lib/features/auth/presentation/screens/magic_link_screen.dart Tier 2 (Deep) 
authStateProvider

MD

4 ProfileSetupScreen /profile-setup lib/features/profile_setup/presentation/screens/profile_setup_screen.dart Tier 1 (Standard) 
profileSetupControllerProvider

MD

5 SanctuaryNavigationShell /main lib/features/navigation/presentation/screens/sanctuary_navigation_shell.dart Tier 2 (Deep) 
navigationIndexProvider, themeProvider

MD

6 FeedScreen /main (Tab 0) lib/features/feed/presentation/screens/feed_screen.dart Tier 1 & Tier 4 (Veil) 
feedControllerProvider

MD

7 ResonancesScreen /main (Tab 1) lib/features/resonances/presentation/screens/resonances_screen.dart Tier 1 (Standard) 
resonancesControllerProvider

MD

8 ChatsListScreen /main (Tab 2) lib/features/chat/presentation/screens/chats_list_screen.dart Tier 1 (Standard) 
chatsListControllerProvider

MD

9 GrowthHubScreen /growth (Tab 3) lib/features/rewards/presentation/screens/growth_hub_screen.dart Tier 1 (Standard) 
growthHubControllerProvider

MD

10 MyPersonaScreen /main (Tab 4) lib/features/profile/presentation/screens/my_persona_screen.dart Tier 1 (Standard) 
myPersonaControllerProvider

MD

11 IgnoredProfilesScreen /ignored-profiles lib/features/feed/presentation/screens/ignored_profiles_screen.dart Tier 1 (Standard) 
feedControllerProvider

MD

12 ChatDialogueScreen /chat-dialogue lib/features/chat/presentation/screens/chat_dialogue_screen.dart Tier 1 & Tier 2 
chatDialogueControllerProvider

MD

13 SeekerProfileDetailScreen /seeker-detail lib/features/profile/presentation/screens/seeker_profile_detail_screen.dart Tier 1 & Tier 4 (Veil) 
seekerProfileControllerProvider

MD

14 BlindDateHubScreen /blind-date lib/features/blind_date/presentation/screens/blind_date_hub_screen.dart Tier 1 (Standard) 
blindDateControllerProvider

MD

15 BlindDateSessionScreen /blind-date-session lib/features/blind_date/presentation/screens/blind_date_session_screen.dart Tier 2 & Tier 4 (Veil) 
blindDateSessionControllerProvider

MD

16 EvaSanctuaryScreen /eva-sanctuary lib/features/ai_sanctuary/presentation/screens/eva_sanctuary_screen.dart Tier 1 (Standard) 
evaSanctuaryControllerProvider

MD

17 VaultLegalScreen /vault lib/features/legal_vault/presentation/screens/vault_legal_screen.dart Tier 1 (Standard) 
vaultControllerProvider

MD

18 SanctuarySettingsScreen /settings lib/features/settings/presentation/screens/sanctuary_settings_screen.dart Tier 1 (Standard) 
settingsControllerProvider, themeProvider

MD

19 SuperadminKycDeskScreen /admin/kyc-desk lib/features/settings/presentation/screens/superadmin_kyc_desk_screen.dart Tier 1 (Standard) 
superadminKycControllerProvider

MD

— SanctuaryAppInfoScreen /app-info lib/features/settings/presentation/screens/sanctuary_app_info_screen.dart Tier 1 (Standard) 
None (Static Info)
MD

1. Condition C4: Responsive Web & PWA Shell Containers
To meet the Condition C4 mandate (Native Android + Zero-Apple-Fee iOS/Desktop PWA), all viewports are wrapped with responsive adaptors.
MD

2.1 Desktop Titanium Mockup Container (ResponsiveDesktopFrame)
For browser viewports
≥
600
px
≥600px, the app is rendered inside a centered mobile frame with ambient radial glows and a dynamic island header.
MD

Dart

// lib/features/navigation/presentation/widgets/responsive_desktop_frame.dart
import 'package:flutter/material.dart';
import '../../../../core/theme/glass_tokens.dart';

class ResponsiveDesktopFrame extends StatelessWidget {
  final Widget child;

  const ResponsiveDesktopFrame({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 600) {
          return child;
        }

        final isDark = Theme.of(context).brightness == Brightness.dark;
        final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

        return Scaffold(
          backgroundColor: tokens.backgroundCanvas,
          body: Stack(
            children: [
              // Ambient Background Glow Orbs
              Positioned(
                top: -100,
                left: -100,
                child: Container(
                  width: 450,
                  height: 450,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: tokens.glowPine,
                  ),
                ),
              ),
              Positioned(
                bottom: -150,
                right: -150,
                child: Container(
                  width: 500,
                  height: 500,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: tokens.glowTerracotta,
                  ),
                ),
              ),
              // Centered Mobile Mockup Container
              Center(
                child: Container(
                  width: 430,
                  height: 890,
                  margin: const EdgeInsets.symmetric(vertical: 24),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(44),
                    border: Border.all(
                      color: tokens.borderSpecularStart,
                      width: 2.5,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.45),
                        blurRadius: 50,
                        spreadRadius: 10,
                        offset: const Offset(0, 20),
                      ),
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(41.5),
                    child: child,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

MD

2.2 iOS Safari PWA Install Banner (IosPwaInstallBanner)
Prompts standalone Safari users to install the web app to bypass the App Store fee.
MD

Dart

// lib/features/navigation/presentation/widgets/ios_pwa_install_banner.dart
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

class IosPwaInstallBanner extends StatefulWidget {
  const IosPwaInstallBanner({super.key});

  @override
  State<IosPwaInstallBanner> createState() => _IosPwaInstallBannerState();
}

class _IosPwaInstallBannerState extends State<IosPwaInstallBanner> {
  bool _dismissed = false;

  @override
  Widget build(BuildContext context) {
    if (!kIsWeb || defaultTargetPlatform != TargetPlatform.iOS || _dismissed) return const SizedBox.shrink();

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return SanctuaryGlassContainer(
      margin: const EdgeInsets.all(12),
      borderRadius: 16,
      blurSigma: 14,
      customTint: tokens.glassTintElevated,
      child: Row(
        children: [
          Icon(Icons.ios_share, color: SanctuaryGlassTokens.brandSacredGold, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  "Install Sanctuary Sanctuary App",
                  style: TextStyle(
                    fontFamily: 'PlayfairDisplay',
                    fontWeight: FontWeight.w700,
                    fontSize: 13.5,
                    color: tokens.textPrimary,
                  ),
                ),
                Text(
                  "Tap 'Share' and select 'Add to Home Screen' for the native experience.",
                  style: TextStyle(
                    fontFamily: 'PlusJakartaSans',
                    fontSize: 11,
                    color: tokens.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: Icon(Icons.close, size: 18, color: tokens.textTertiary),
            onPressed: () => setState(() => _dismissed = true),
          ),
        ],
      ),
    );
  }
}

MD

1. Screen-by-Screen Detailed Blueprints
Cluster A: Onboarding & Statutory Gates (Screens 1 – 4)
Screen 1: ConsentScreen (/consent)
Purpose: First launch screen presenting DPDP Act 2023 purpose limitations, 18+ age criteria, and theme selection.
MD

Glass Styling: Tier 1 SanctuaryGlassContainer wrapping agreement clauses, resting above an ambient light gradient canvas.
MD

Components:

Editorial Header: PlayfairDisplay title: "Welcome to UR-Heart Sanctuary".
MD

3 Scrollable Frosted Consent Cards: DPDP Section 6 Purpose Limitation, Anti-Screenshot FLAG_SECURE notification, and No-Doomscrolling 10-Swipe rule.
MD

Theme Toggle Pill: Quick toggle between Dark Sanctuary and Light Sanctuary.
MD

CTA Button: Frosted button with glowing border: "I Affirm & Enter the Sanctuary".
MD

Screen 2: AgeGateAuthScreen (/auth)
Purpose: Strict 18+ Date-of-Birth gate paired with Google Sign-In and Magic Link entry.
MD

Glass Styling: Deep frosted central card (blurSigma: 16.0) with translucent inputs.
MD

Logic Handshake:

Seeker selects DOB via Cupertino glass date picker.

If calculated age
<
18
<18: Triggers underage_quarantine_registry hardware lockout for 180 days.
MD

If
≥
18
≥18: Unlocks Google Sign-In and passwordless email fields.
MD

Components:

DOB Selection Tile: Shows age dynamically with affirmative badge if
≥
18
≥18.
MD

Google One-Tap Action: Branded glass container dispatching RS256 token exchange.
MD

Magic Link Input: Email text field with 1px specular gradient outline and dispatch button.
MD

Screen 3: MagicLinkScreen (/magic-link)
Purpose: Intercepts deep-linked auth tokens (/magic-link?token=...) and handles session bootstrapping.
MD

Glass Styling: Centered SanctuaryGlassContainer (blurSigma: 20.0) with a circular progress indicator accented by brandSacredGold.
MD

Components:

Animated Gold Ring: Refracting inner pulse animation.
MD

Status Feedback: Text label: "Unlocking your Sanctuary session..."

MD

Error Shield: Renders error messages with an "Ask for new link" fallback button.
MD

Screen 4: ProfileSetupScreen (/profile-setup)
Purpose: Onboarding wizard covering 5 photo slots, bio, voice spark prompt, and Groq facial verification.
MD

Glass Styling: Grid of frosted upload frames with terracotta active borders.
MD

Components:

5-Slot Photo Grid: Translucent placeholder rectangles displaying slot numbers (slot_1.webp through slot_5.webp) with upload triggers.
MD

Bio Prose Editor: Translucent text container with character counter (max 500) and an "Eva AI Polish" quick trigger.
MD

Voice Spark Audio Recorder: 7-second mic recorder button showing audio amplitude waveforms.
MD

KYC Selfie Trigger: Opens camera modal for 3-second live selfie video verification.
MD

Cluster B: Sanctuary Shell & Primary 5 Tabs (Screens 5 – 10)
┌────────────────────────────────────────────────────────────────────────┐
│             SanctuaryNavigationShell (/main Architecture)              │
├────────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ GlassAppBar (Top: Sanctuary Logo, Active Streak Badge, Slumber)    │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│            [ IndexedStack: Tab 0 | Tab 1 | Tab 2 | Tab 3 | Tab 4 ]      │
│                                                                        │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ GlassBottomNavBar (Floating: Feed | Resonances | Chat | Store | Me)│ │
│ └────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘

MD

Screen 5: SanctuaryNavigationShell (/main)
Purpose: Master navigation scaffold hosting the persistent top GlassAppBar, 5 tab views via IndexedStack, and the floating GlassBottomNavBar.
MD

Components:

Persistent GlassAppBar: Displays Sanctuary logo, streak counter pill (streak_count), and night slumber icon.
MD

IndexedStack: Retains tab state across navigation switching.
MD

Floating GlassBottomNavBar: Frosted pill navigation bar fixed above the bottom safe area.
MD

Screen 6: FeedScreen (/main - Tab 0: Discovery Deck)
Purpose: Core discovery feed enforcing the 10-swipe daily quota, reciprocal orientation filters, and the 35px photo blur veil.
MD

Glass Styling: Stack of swipeable frosted discovery cards (sigmaX: 12.0) featuring GlassVeilWidget.
MD

Components:

Discovery Card Deck: Profile cards with name, age, city (~1.1 km fuzzed), profession, and bio.
MD

GlassVeilWidget: 35px Gaussian blur veil masking photos until bilateral revelation.
MD

Voice Spark Player: Embedded player for the 7-second audio snippet.
MD

Floating Glass Actions: Circular frosted buttons for Pass (left), Direct Letter (center, gold), and Like (right, terracotta).
MD

Daily Quota Pill: Top indicator tracking remaining swipes (swipes_remaining).
MD

Screen 7: ResonancesScreen (/main - Tab 1: Incoming & Sparks)
Purpose: Displays incoming likes, mutual affinities, and unopened Direct Letters.
MD

Glass Styling: Two-column staggered grid of frosted tiles with emerald/gold border highlights.
MD

Components:

Tab Selector: Frosted toggle switch between "Incoming Sparks" and "Mutual Resonances".
MD

Resonant Profile Cards: Veiled profile tiles featuring mutual affinity badges.
MD

Direct Letter Envelopes: Gold-accented cards displaying thoughtful initial notes.
MD

Screen 8: ChatsListScreen (/main - Tab 2: Dialogue Inbox)
Purpose: Directory of active 1:1 encrypted kinship dialogues.
MD

Glass Styling: Frosted list tiles with 1px specular dividers and unread glow badges.
MD

Components:

Search Bar: Frosted search input filter.
MD

Dialogue Row Items: Rounded avatar, seeker name, last message snippet, timestamp, and read receipt tick.
MD

Sacred Bridge Status Chip: Indicates whether contact info is unsealed.
MD

Screen 9: GrowthHubScreen (/growth - Tab 3: Store & Rewards)
Purpose: Monetization hub handling micro-perks, pass tiers (Condition C2), rewarded ads, and sleep multipliers.
MD

Glass Styling: Premium gold and obsidian glass containers with specular borders.
MD

Components:

Mindful Streak Gauge: Radial progress display showing hours until streak expiration.
MD

Night Slumber Card: Displays accelerometer sleep detection state and multiplier (1.5x–2.0x).
MD

Rewarded Ad Triggers: 4 reflection ad cards (Quick Reflection, Deep Resonance, Sacred Bridge, Harvest).
MD

Sovereign Store: In-app purchase cards with INR pricing buttons (Direct Letter ₹29, Passes).
MD

Screen 10: MyPersonaScreen (/main - Tab 4: Seeker Profile)
Purpose: Authenticated seeker profile preview, settings navigation, and privacy modes.
MD

Glass Styling: Frosted surface card showcasing the seeker's public profile.
MD

Components:

Profile Header: Avatar, KYC verification badge, and Sovereign status pill.
MD

Voice Spark Re-record Card: Audio player with edit options.
MD

Privacy Mode Toggles: Glass switch tiles for Incognito Mode, Discreet Mode, and Slumber Mode.
MD

Account Management Group: Entry buttons for Settings, Legal Vault, and App Info.
MD

Cluster C: Kinship Dialogue, Aux Discovery & Seeker Detail (Screens 11 – 13)
Screen 11: IgnoredProfilesScreen (/ignored-profiles)
Purpose: The "Pass Vault" allowing seekers to reconsider and resurrect previously skipped profiles.
MD

Glass Styling: Dimmed frosted tiles (opacity: 0.10) with glowing reset buttons.
MD

Components:

Archived Profile List: List of passed seekers within the 30-day retention window.
MD

Resurrect Action Button: Restores the profile back into the discovery deck.
MD

Screen 12: ChatDialogueScreen (/chat-dialogue)
Purpose: Real-time 1:1 encrypted dialogue chamber with E2EE messaging and Sacred Contact Bridge.
MD

Hardware Enforcement: FLAG_SECURE = 8192 enabled to block screenshots and recording.
MD

Glass Styling:

Sender bubbles: Glass tint with terracotta border.
MD

Peer bubbles: Deep frosted glass tint with slate border.
MD

Floating Input Bar: Frosted container anchored above the keyboard.
MD

Components:

Dialogue Header: Peer avatar, active presence dot (onlineEmerald), Sacred Bridge button, and menu.
MD

Message List: Chronological list of encrypted chat bubbles, timestamps, and delivery/read ticks.
MD

Sacred Bridge Banner: Top notification prompting mutual contact handle unsealing.
MD

Wingman Suggestion Tray: Frosted tray providing empathetic reply ideas powered by Gemini 2.5 Flash.
MD

Action Menu: Triggers "Pass with Grace" closure or grievance reporting.
MD

Screen 13: SeekerProfileDetailScreen (/seeker-detail)
Purpose: Full-screen profile view with expandable values bio, traits, and photo veil controls.
MD

Hardware Enforcement: Protected by FLAG_SECURE = 8192.
MD

Glass Styling: Scrollable glass sheet overlaying the 35px veiled photo background.
MD

Components:

Hero Image Canvas: Dynamic background featuring GlassVeilWidget.
MD

Values & Lifestyle Chips: Frosted pills for personality traits and interests.
MD

Voice Spark Waveform Player: Plays the 7-second voice introduction.
MD

Photo Reveal Request Button: Triggers bilateral unmasking consent.
MD

Cluster D: Condition C1 Fast-Track Subsystem (Screens 14 – 15)
Screen 14: BlindDateHubScreen (/blind-date)
Purpose: Matchmaking hub for anonymous 180s live dialogue, gated behind the 1M active users milestone.
MD

Gate Enforcement: Shows MilestoneProgressIndicator if active MAU < 1,000,000 and override is disabled.
MD

Glass Styling: Deep midnight glass container with sacred gold progress accents.
MD

Components:

Milestone Lock Card: Visual indicator tracking progress toward 1,000,000 active seekers with explanatory dialog.
MD

Daily Pass Balance: Available passes count (blind_date_passes).
MD

Queue Action Button: Joins the anonymous pairing queue.
MD

Screen 15: BlindDateSessionScreen (/blind-date-session)
Purpose: 180-second live anonymous chat room featuring veiled photos and Eva icebreaker prompts (with optional +180s mutual extension).
MD

Hardware Enforcement: Protected by FLAG_SECURE = 8192.
MD

Glass Styling: High-diffusion frosted chat container (sigmaX: 20.0) with countdown ring.
MD

Components:

Circular Countdown Timer: Arc animation counting down from 180s to 0s.
MD

Veiled Mirror Card: Shows peer's age and gender behind a 35px blur veil.
MD

Eva Icebreaker Banner: Curated conversational prompt injected into the session.
MD

Action Footer: Dual decision buttons: "Mindful Bow" (Pass) and "Resonate" (Mutual match).
MD

Cluster E: AI Sanctuary, Legal Vault & Governance (Screens 16 – 19)
Screen 16: EvaSanctuaryScreen (/eva-sanctuary)
Purpose: Dedicated conversational space with synthetic companions Eva or Arjun.
MD

Glass Styling: Frosted chat viewport with floating prompt suggestion chips.
MD

Components:

Companion Selector: Glass switch between Eva and Arjun.
MD

Dialogue Stream: Roman Hindi/English supportive conversational interface.
MD

Chat Sparks Carousel: Quick conversation starters for personal reflection.
MD

Screen 17: VaultLegalScreen (/vault)
Purpose: DPDP Act 2023 compliance center managing data portability, nominee rights, and grievances.
MD

Glass Styling: Structural glass cards organized in an administrative layout.
MD

Components:

Data Portability Card (Section 11): Button to request and download signed data export archive.
MD

Digital Nominee Tile (Section 14): Manage legal representative for account data.
MD

Grievance Register: Submit and track incident dossiers under IT Rules 2021.
MD

Statutory Directory: Links to the 8 legal SSR portals (/privacy, /terms, etc.).
MD

Screen 18: SanctuarySettingsScreen (/settings)
Purpose: Privacy controls, notification channels, and account lifecycle settings.
MD

Glass Styling: Clean frosted list tiles with subtle trailing chevron icons.
MD

Components:

Security Controls: Toggle switches for Incognito Mode, Discreet App Icon, and FCM notifications.
MD

Account Erasure Tile: Red-tinted button routing to two-step account deletion.
MD

Sign Out Action: Clears Android Keystore session securely.
MD

Screen 19: SuperadminKycDeskScreen (/admin/kyc-desk)
Purpose: Administrative review interface for escalated biometric verification tickets.
MD

Glass Styling: Split-panel workstation with dual media preview containers.
MD

Components:

Split Glass Media Viewer: Side-by-side comparison of anchor photo against selfie video.
MD

AI Scoring Dossier: Displays Groq match score and reasoning notes.
MD

Action Controls: Approve and Reject buttons logging to admin_audit_logs.
MD

1. Reusable Interactive Glass Modals & Bottom Sheets
4.1 Mindful Closure Sheet ("Pass with Grace")
Allows seekers to respectfully end a dialogue using curated closure templates rather than abrupt unmatching.
MD

Dart

// lib/features/chat/presentation/widgets/pass_with_grace_dialog.dart
import 'package:flutter/material.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

class PassWithGraceDialog extends StatelessWidget {
  final Function(String templateKey, String? note) onConfirmClosure;

  const PassWithGraceDialog({super.key, required this.onConfirmClosure});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 20),
      child: SanctuaryGlassContainer(
        borderRadius: 24,
        blurSigma: 24, // Tier 3 Modal Glass
        customTint: tokens.glassTintSecondary,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Icon(Icons.spa_outlined, color: SanctuaryGlassTokens.brandPine, size: 36),
            const SizedBox(height: 12),
            Text(
              "Part Ways with Grace",
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: 'PlayfairDisplay',
                fontWeight: FontWeight.w700,
                fontSize: 20,
                color: tokens.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              "Ghosting shocks the spirit. Select a mindful closure thought to conclude this kinship with dignity.",
              textAlign: TextAlign.center,
              style: TextStyle(fontFamily: 'PlusJakartaSans', fontSize: 13, color: tokens.textSecondary),
            ),
            const SizedBox(height: 16),
            _buildTemplateTile(context, "grace_paths_diverge", "Our paths diverge, but I honor our shared dialogue."),
            _buildTemplateTile(context, "grace_not_aligned", "I felt our core rhythms differ, wishing you clarity."),
            _buildTemplateTile(context, "grace_holding_space", "Taking time for quiet solitude; bowing out with gratitude."),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              style: ElevatedButton.styleFrom(
                backgroundColor: tokens.glassTintElevated,
                foregroundColor: tokens.textPrimary,
                elevation: 0,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              child: const Text("Remain in Dialogue"),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTemplateTile(BuildContext context, String key, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: InkWell(
        onTap: () {
          Navigator.pop(context);
          onConfirmClosure(key, null);
        },
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.white.withOpacity(0.1)),
          ),
          child: Text(text, style: const TextStyle(fontFamily: 'PlusJakartaSans', fontSize: 12)),
        ),
      ),
    );
  }
}

MD

4.2 Sacred Contact Bridge Reveal Sheet
Facilitates bilateral contact handle exchange via mindful ad completion or instant key.
MD

Dart

// lib/features/chat/presentation/widgets/sacred_bridge_sheet.dart
import 'package:flutter/material.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

class SacredBridgeSheet extends StatelessWidget {
  final int userAdsWatched;
  final int partnerAdsWatched;
  final VoidCallback onWatchAd;
  final VoidCallback onInstantUnlock;

  const SacredBridgeSheet({
    super.key,
    required this.userAdsWatched,
    required this.partnerAdsWatched,
    required this.onWatchAd,
    required this.onInstantUnlock,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return SanctuaryGlassContainer(
      borderRadius: 28,
      blurSigma: 24, // Tier 3 Modal Glass
      customTint: tokens.glassTintSecondary,
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.vpn_key_outlined, color: SanctuaryGlassTokens.brandSacredGold, size: 40),
          const SizedBox(height: 12),
          Text(
            "The Sacred Contact Bridge",
            style: TextStyle(
              fontFamily: 'PlayfairDisplay',
              fontWeight: FontWeight.w700,
              fontSize: 22,
              color: tokens.textPrimary,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            "External communication channels require mutual cryptographic consent. Complete the 3-ad mindfulness ritual together, or use an Instant Bridge Key.",
            textAlign: TextAlign.center,
            style: TextStyle(fontFamily: 'PlusJakartaSans', fontSize: 13, color: tokens.textSecondary),
          ),
          const SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _buildProgressCircle("Your Consent", userAdsWatched, 3),
              _buildProgressCircle("Partner Consent", partnerAdsWatched, 3),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: onWatchAd,
                  style: OutlinedButton.styleFrom(
                    side: BorderSide(color: SanctuaryGlassTokens.brandPine),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  child: const Text("Watch Ad (1/3)"),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton(
                  onPressed: onInstantUnlock,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: SanctuaryGlassTokens.brandSacredGold,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  child: const Text("Instant Key ₹99"),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildProgressCircle(String label, int current, int total) {
    return Column(
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            CircularProgressIndicator(
              value: current / total,
              color: SanctuaryGlassTokens.brandSacredGold,
              backgroundColor: Colors.white.withOpacity(0.1),
            ),
            Text("$current/$total", style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
          ],
        ),
        const SizedBox(height: 6),
        Text(label, style: const TextStyle(fontSize: 11)),
      ],
    );
  }
}

MD

1. UI Acceptance & Quality Assurance Checklist
To verify screen rendering and interactive state handling:

Bash

# 1. Verify Android Keystore security, Window FLAG_SECURE & Onboarding test suites

flutter test test/test_window_security_policy.dart test/milestone4_onboarding_screens_test.dart

# 2. Verify iOS PWA install banner and desktop frame responsive layouts

flutter test test/ios_pwa_and_laptop_web_test.dart

# 3. Verify static analysis across all presentation files

dart analyze lib/features
