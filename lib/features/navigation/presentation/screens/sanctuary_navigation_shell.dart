import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/glass_navigation_shell_bars.dart';
import '../../../chat/presentation/screens/chats_list_screen.dart';
import '../../../feed/presentation/screens/feed_screen.dart';
import '../../../profile/presentation/screens/my_persona_screen.dart';
import '../../../resonances/presentation/screens/resonances_screen.dart';
import '../../../rewards/presentation/screens/growth_hub_screen.dart';

/// Screen 5: SanctuaryNavigationShell (/main Architecture)
/// Master navigation scaffold hosting the persistent 5 tab views via IndexedStack
/// and the floating frosted GlassBottomNavBar.
class SanctuaryNavigationShell extends ConsumerStatefulWidget {
  const SanctuaryNavigationShell({super.key});

  @override
  ConsumerState<SanctuaryNavigationShell> createState() =>
      _SanctuaryNavigationShellState();
}

class _SanctuaryNavigationShellState
    extends ConsumerState<SanctuaryNavigationShell> {
  int _currentIndex = 0;

  static const List<Widget> _tabs = [
    FeedScreen(),
    ResonancesScreen(),
    ChatsListScreen(),
    GrowthHubScreen(),
    MyPersonaScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens =
        isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: Stack(
        children: [
          // 1. IndexedStack retaining tab states
          IndexedStack(
            index: _currentIndex,
            children: _tabs,
          ),

          // 2. Floating Frosted Glass Bottom Navigation Bar
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: GlassBottomNavBar(
              currentIndex: _currentIndex,
              onTap: (index) {
                setState(() => _currentIndex = index);
              },
              items: const [
                BottomNavigationBarItem(
                  icon: Icon(Icons.style_outlined),
                  activeIcon: Icon(Icons.style_rounded),
                  label: 'Feed',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.favorite_border_rounded),
                  activeIcon: Icon(Icons.favorite_rounded),
                  label: 'Resonance',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.chat_bubble_outline_rounded),
                  activeIcon: Icon(Icons.chat_bubble_rounded),
                  label: 'Dialogue',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.spa_outlined),
                  activeIcon: Icon(Icons.spa_rounded),
                  label: 'Growth',
                ),
                BottomNavigationBarItem(
                  icon: Icon(Icons.person_outline_rounded),
                  activeIcon: Icon(Icons.person_rounded),
                  label: 'Sanctuary',
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
