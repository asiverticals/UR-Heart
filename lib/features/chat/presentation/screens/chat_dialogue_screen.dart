import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../../core/constants/app_typography.dart';
import '../../../../core/services/window_security_service.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';
import '../../domain/models/chat_message.dart';
import '../controllers/chat_dialogue_controller.dart';
import '../widgets/pass_with_grace_dialog.dart';

/// 1:1 Encrypted Dialogue Viewport with Living Frosted-Glass Styling and Hardware Screen Security.
class ChatDialogueScreen extends ConsumerStatefulWidget {
  final String matchId;
  final String peerId;
  final String peerName;

  const ChatDialogueScreen({
    super.key,
    required this.matchId,
    required this.peerId,
    this.peerName = 'Soul Seeker',
  });

  @override
  ConsumerState<ChatDialogueScreen> createState() => _ChatDialogueScreenState();
}

class _ChatDialogueScreenState extends ConsumerState<ChatDialogueScreen> {
  final TextEditingController _textController = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    // 1. Hardware Screen Security Invariant (FLAG_SECURE = 8192)
    WindowSecurityService.enforceWindowProtection('/chat-dialogue');

    // 2. Initialize dialogue session and real-time socket subscription
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(chatDialogueControllerProvider(widget.matchId).notifier)
          .initializeDialogue(widget.matchId, widget.peerId);
    });
  }

  @override
  void dispose() {
    // Relax hardware window protection on leaving dialogue chamber
    WindowSecurityService.relaxWindowProtection();
    _textController.dispose();
    _focusNode.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleSend() {
    final text = _textController.text;
    if (text.trim().isEmpty) return;

    final controller = ref.read(chatDialogueControllerProvider(widget.matchId).notifier);
    controller.sendTextMessage(text);
    _textController.clear();
    controller.sendTyping(false);
  }

  void _openPassWithGraceDialog() {
    PassWithGraceDialog.show(
      context,
      onConfirmClosure: (templateKey, note) async {
        final controller = ref.read(chatDialogueControllerProvider(widget.matchId).notifier);
        return await controller.closeWithGrace(templateKey, note);
      },
    );
  }

  void _openReportGrievanceDialog() {
    context.push('/vault?reported_user_id=${widget.peerId}');
  }

  void _openBlockSeekerDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Block Seeker?'),
        content: const Text(
          'Blocking this seeker will immediately sever your mutual resonance, conclude the chat dialogue, and remove their persona from discovery deck.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.redAccent),
            onPressed: () async {
              Navigator.of(ctx).pop();
              final controller = ref.read(chatDialogueControllerProvider(widget.matchId).notifier);
              final blocked = await controller.blockPeer(widget.peerId, reason: 'safety_concern');
              if (blocked && mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Seeker has been blocked.')),
                );
                context.pop();
              }
            },
            child: const Text('Block', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();
    final chatState = ref.watch(chatDialogueControllerProvider(widget.matchId));

    // Invert messages list for reverse: true ListView
    final reversedMessages = chatState.messages.reversed.toList();

    return Scaffold(
      backgroundColor: tokens.backgroundCanvas,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // 1. Glass Top Bar
            _buildGlassTopBar(context, tokens, chatState),

            // 2. Active Messages Chamber
            Expanded(
              child: chatState.isLoadingHistory
                  ? const Center(
                      child: CircularProgressIndicator(
                        strokeWidth: 2.0,
                        color: SanctuaryGlassTokens.brandTerracotta,
                      ),
                    )
                  : Stack(
                      children: [
                        // Messages List
                        ListView.builder(
                          controller: _scrollController,
                          reverse: true,
                          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                          itemCount: reversedMessages.length,
                          itemBuilder: (context, index) {
                            final message = reversedMessages[index];
                            final isSender = message.senderId != widget.peerId;
                            return _buildMessageBubble(
                              message: message,
                              isSender: isSender,
                              tokens: tokens,
                            );
                          },
                        ),

                        // Typing indicator banner
                        if (chatState.isPeerTyping)
                          Positioned(
                            left: 16.0,
                            bottom: 8.0,
                            child: _buildTypingIndicatorChip(tokens),
                          ),
                      ],
                    ),
            ),

            // 3. Concluded Dialogue Banner OR Floating Glass Input Bar
            if (chatState.isDialogueClosed)
              _buildClosedDialogueBanner(tokens, chatState.closureTemplateKey)
            else
              _buildFloatingInputBar(tokens, chatState),
          ],
        ),
      ),
    );
  }

  Widget _buildGlassTopBar(
    BuildContext context,
    SanctuaryGlassTokens tokens,
    ChatDialogueState state,
  ) {
    return SanctuaryGlassContainer(
      borderRadius: 0,
      blurSigma: 16.0,
      borderWidth: 0.5,
      padding: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 8.0),
      child: Row(
        children: [
          // Back button
          IconButton(
            icon: Icon(Icons.arrow_back_ios_new_rounded, size: 20.0, color: tokens.textPrimary),
            onPressed: () => Navigator.of(context).maybePop(),
          ),

          // Peer Avatar with Live Presence Indicator
          Stack(
            clipBehavior: Clip.none,
            children: [
              CircleAvatar(
                radius: 19.0,
                backgroundColor: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.2),
                child: Text(
                  widget.peerName.isNotEmpty ? widget.peerName[0].toUpperCase() : 'S',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    color: SanctuaryGlassTokens.brandTerracotta,
                    fontSize: 15.0,
                  ),
                ),
              ),
              if (state.isPeerOnline && !state.isDialogueClosed)
                Positioned(
                  right: 0,
                  bottom: 0,
                  child: Container(
                    width: 10.0,
                    height: 10.0,
                    decoration: BoxDecoration(
                      color: SanctuaryGlassTokens.onlineEmerald,
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: tokens.backgroundCanvas,
                        width: 1.5,
                      ),
                    ),
                  ),
                ),
            ],
          ),
          const SizedBox(width: 12.0),

          // Peer Name & Status
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  widget.peerName,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontWeight: FontWeight.w600,
                    fontSize: 15.0,
                    color: tokens.textPrimary,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  state.isDialogueClosed
                      ? 'Dialogue Concluded'
                      : (state.isPeerTyping ? 'Mindfully typing...' : 'Soulful presence'),
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 11.5,
                    color: state.isDialogueClosed
                        ? tokens.textTertiary
                        : (state.isPeerTyping
                            ? SanctuaryGlassTokens.brandTerracotta
                            : SanctuaryGlassTokens.onlineEmerald),
                  ),
                ),
              ],
            ),
          ),

          // Options Menu: "Pass with Grace"
          PopupMenuButton<String>(
            icon: Icon(Icons.more_vert_rounded, color: tokens.textPrimary),
            color: tokens.elevatedSurface,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14.0)),
            onSelected: (value) {
              if (value == 'pass_with_grace') {
                _openPassWithGraceDialog();
              } else if (value == 'report_grievance') {
                _openReportGrievanceDialog();
              } else if (value == 'block_seeker') {
                _openBlockSeekerDialog();
              }
            },
            itemBuilder: (ctx) => [
              if (!state.isDialogueClosed)
                const PopupMenuItem(
                  value: 'pass_with_grace',
                  child: Row(
                    children: [
                      Icon(Icons.spa_outlined, size: 18.0, color: SanctuaryGlassTokens.brandPine),
                      SizedBox(width: 10.0),
                      Text('Pass with Grace'),
                    ],
                  ),
                ),
              const PopupMenuItem(
                value: 'report_grievance',
                enabled: true,
                child: Row(
                  children: [
                    Icon(Icons.flag_outlined, size: 18.0, color: Colors.amber),
                    SizedBox(width: 10.0),
                    Text('Report Grievance'),
                  ],
                ),
              ),
              const PopupMenuItem(
                value: 'block_seeker',
                enabled: true,
                child: Row(
                  children: [
                    Icon(Icons.block_outlined, size: 18.0, color: Colors.redAccent),
                    SizedBox(width: 10.0),
                    Text('Block Seeker'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble({
    required ChatMessage message,
    required bool isSender,
    required SanctuaryGlassTokens tokens,
  }) {
    final timeStr = DateFormat('hh:mm a').format(message.createdAt.toLocal());

    return Align(
      alignment: isSender ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.76,
        ),
        margin: const EdgeInsets.symmetric(vertical: 4.0),
        child: isSender
            // Sender bubble: Terracotta specular border with glass tint
            ? SanctuaryGlassContainer(
                borderRadius: 16.0,
                blurSigma: 12.0,
                borderWidth: 1.0,
                customBorderGradient: const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    SanctuaryGlassTokens.brandTerracotta,
                    SanctuaryGlassTokens.brandTerracottaGlow,
                  ],
                ),
                customTint: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.16),
                padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 10.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      message.encryptedText,
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 14.0,
                        height: 1.35,
                        color: tokens.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4.0),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          timeStr,
                          style: TextStyle(
                            fontSize: 10.5,
                            color: tokens.textTertiary,
                          ),
                        ),
                        const SizedBox(width: 4.0),
                        _buildStatusIcon(message.status),
                      ],
                    ),
                  ],
                ),
              )
            // Peer bubble: Deep frosted slate glass tint with subtle border
            : SanctuaryGlassContainer(
                borderRadius: 16.0,
                blurSigma: 12.0,
                borderWidth: 1.0,
                customTint: tokens.glassTintSecondary,
                padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 10.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      message.encryptedText,
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 14.0,
                        height: 1.35,
                        color: tokens.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 4.0),
                    Text(
                      timeStr,
                      style: TextStyle(
                        fontSize: 10.5,
                        color: tokens.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
      ),
    );
  }

  Widget _buildStatusIcon(String status) {
    switch (status) {
      case 'sending':
        return const Icon(Icons.access_time_rounded, size: 12.0, color: Colors.grey);
      case 'sent':
        return const Icon(Icons.done_rounded, size: 14.0, color: Colors.grey);
      case 'delivered':
        return const Icon(Icons.done_all_rounded, size: 14.0, color: Colors.grey);
      case 'read':
        return const Icon(Icons.done_all_rounded, size: 14.0, color: SanctuaryGlassTokens.tickCyan);
      default:
        return const Icon(Icons.done_rounded, size: 14.0, color: Colors.grey);
    }
  }

  Widget _buildTypingIndicatorChip(SanctuaryGlassTokens tokens) {
    return SanctuaryGlassContainer(
      borderRadius: 12.0,
      blurSigma: 8.0,
      padding: const EdgeInsets.symmetric(horizontal: 10.0, vertical: 5.0),
      customTint: tokens.glassTintSecondary,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.more_horiz_rounded, size: 16.0, color: SanctuaryGlassTokens.brandTerracotta),
          const SizedBox(width: 4.0),
          Text(
            '${widget.peerName} is typing...',
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              fontSize: 11.5,
              fontStyle: FontStyle.italic,
              color: tokens.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildClosedDialogueBanner(
    SanctuaryGlassTokens tokens,
    String? templateKey,
  ) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
      decoration: BoxDecoration(
        color: tokens.elevatedSurface.withValues(alpha: 0.9),
        border: Border(
          top: BorderSide(
            color: tokens.borderSpecularStart.withValues(alpha: 0.3),
            width: 1.0,
          ),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.spa_outlined, size: 24.0, color: SanctuaryGlassTokens.brandPine),
          const SizedBox(height: 6.0),
          Text(
            'This dialogue has concluded with grace. Archived in peace.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: SanctuaryTypography.serifFont,
              fontStyle: FontStyle.italic,
              fontSize: 13.5,
              color: tokens.textPrimary,
            ),
          ),
          const SizedBox(height: 4.0),
          Text(
            'Chamber is sealed in accordance with modesty-first principles.',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontFamily: SanctuaryTypography.sansFont,
              fontSize: 11.0,
              color: tokens.textTertiary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFloatingInputBar(
    SanctuaryGlassTokens tokens,
    ChatDialogueState state,
  ) {
    return SanctuaryGlassContainer(
      borderRadius: 0,
      blurSigma: 18.0, // Floating glass input bar invariant
      borderWidth: 1.0,
      padding: EdgeInsets.only(
        left: 14.0,
        right: 14.0,
        top: 10.0,
        bottom: MediaQuery.of(context).viewInsets.bottom + 12.0,
      ),
      child: Row(
        children: [
          // Text-Only Input Field (Modesty-first invariant: no camera/file icons)
          Expanded(
            child: TextField(
              controller: _textController,
              focusNode: _focusNode,
              maxLength: 4096,
              maxLines: 4,
              minLines: 1,
              style: TextStyle(
                fontFamily: SanctuaryTypography.sansFont,
                fontSize: 14.0,
                color: tokens.textPrimary,
              ),
              onChanged: (val) {
                final controller = ref.read(chatDialogueControllerProvider(widget.matchId).notifier);
                controller.sendTyping(val.trim().isNotEmpty);
              },
              decoration: InputDecoration(
                counterText: '',
                hintText: 'Speak with mindful intention...',
                hintStyle: TextStyle(
                  fontFamily: SanctuaryTypography.sansFont,
                  fontSize: 13.5,
                  color: tokens.textTertiary,
                ),
                contentPadding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 10.0),
                filled: true,
                fillColor: tokens.glassTintPrimary,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(22.0),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),
          const SizedBox(width: 8.0),

          // Circular Send Button with Terracotta Glow
          Container(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: SanctuaryGlassTokens.brandTerracotta.withValues(alpha: 0.35),
                  blurRadius: 12.0,
                  spreadRadius: 1.0,
                ),
              ],
            ),
            child: IconButton(
              onPressed: state.isSending ? null : _handleSend,
              style: IconButton.styleFrom(
                backgroundColor: SanctuaryGlassTokens.brandTerracotta,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.all(12.0),
              ),
              icon: const Icon(Icons.arrow_upward_rounded, size: 20.0),
            ),
          ),
        ],
      ),
    );
  }
}
