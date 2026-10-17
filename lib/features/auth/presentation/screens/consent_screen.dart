import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../../../core/constants/app_typography.dart';
import '../../../../core/theme/glass_tokens.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/theme/widgets/sanctuary_glass_container.dart';

/// First launch screen presenting DPDP Act 2023 purpose limitations,
/// anti-screenshot FLAG_SECURE notification, and mindful 10-swipe daily limits.
class ConsentScreen extends ConsumerStatefulWidget {
  const ConsentScreen({super.key});

  static const String consentRecordKey = 'dpdp_statutory_consent_record_v1';

  @override
  ConsumerState<ConsentScreen> createState() => _ConsentScreenState();
}

class _ConsentScreenState extends ConsumerState<ConsentScreen> {

  bool _consentPurposeLimitation = false;
  bool _consentAntiCapture = false;
  bool _consentRhythmAllowance = false;
  String _selectedLanguage = 'English';

  static const List<Map<String, String>> _eighthScheduleLanguages = [
    {'name': 'English', 'native': 'English'},
    {'name': 'Hindi', 'native': 'हिन्दी'},
    {'name': 'Bengali', 'native': 'বাংলা'},
    {'name': 'Telugu', 'native': 'తెలుగు'},
    {'name': 'Marathi', 'native': 'मराठी'},
    {'name': 'Tamil', 'native': 'தமிழ்'},
    {'name': 'Gujarati', 'native': 'ગુજરાતી'},
    {'name': 'Kannada', 'native': 'ಕನ್ನಡ'},
    {'name': 'Malayalam', 'native': 'മലയാളം'},
    {'name': 'Odia', 'native': 'ଓଡ଼ିଆ'},
    {'name': 'Punjabi', 'native': 'ਪੰਜਾਬੀ'},
  ];

  static const Map<String, Map<String, String>> _localizedStrings = {
    'English': {
      'header_title': 'Welcome to UR-Heart Sanctuary',
      'header_subtitle': 'A sacred, intentional space honoring digital privacy, conscious connection, and psychological sovereignty.',
      'card_purpose_title': 'DPDP Section 6 Purpose Limitation',
      'card_purpose_desc': 'Under India DPDP Act 2023, personal data is processed solely for sacred matchmaking. Zero third-party data brokerage, zero behavioral ad tracking, and hardware Keystore AES-256 GCM encryption.',
      'card_anticapture_title': 'FLAG_SECURE Anti-Capture Shield',
      'card_anticapture_desc': 'Sanctuary activates OS-level display protection. Screenshots, screen recordings, and external screen cloning are intercepted and blocked at the hardware display pipeline.',
      'card_rhythm_title': '10-Swipe Daily Mindful Rhythm',
      'card_rhythm_desc': 'To protect emotional well-being and eradicate doomscrolling, discovery is limited to 10 conscious profiles daily. Matches require mutual intentionality before dialogue begins.',
    },
    'Hindi': {
      'header_title': 'UR-Heart अभयारण्य में आपका स्वागत है',
      'header_subtitle': 'डिजिटल गोपनीयता, सचेत जुड़ाव और व्यक्तिगत संप्रभुता का सम्मान करने वाला एक पवित्र स्थान।',
      'card_purpose_title': 'DPDP धारा 6 उद्देश्य परिसीमन',
      'card_purpose_desc': 'भारत DPDP अधिनियम 2023 के तहत, व्यक्तिगत डेटा केवल पवित्र मैचमेकिंग के लिए संसाधित किया जाता है। शून्य डेटा ब्रोकरेज और हार्डवेयर कीस्टोर AES-256 एन्क्रिप्शन।',
      'card_anticapture_title': 'FLAG_SECURE एंटी-कैप्चर शील्ड',
      'card_anticapture_desc': 'अभयारण्य ऑपरेटिंग सिस्टम स्तर की सुरक्षा सक्रिय करता है। स्क्रीनशॉट और स्क्रीन रिकॉर्डिंग हार्डवेयर स्तर पर अवरुद्ध हैं।',
      'card_rhythm_title': '10-स्वाइप दैनिक सचेत लय',
      'card_rhythm_desc': 'मानसिक शांति की रक्षा और अत्यधिक उपयोग रोकने के लिए दैनिक खोज 10 प्रोफाइल तक सीमित है।',
    },
    'Bengali': {
      'header_title': 'UR-Heart অভয়ারণ্যে স্বাগতম',
      'header_subtitle': 'ডিজিটাল গোপনীয়তা, সচেতন সংযোগ এবং মানসিক সার্বভৌমত্ব রক্ষার একটি পবিত্র স্থান।',
      'card_purpose_title': 'DPDP ধারা ৬ উদ্দেশ্য সীমাবদ্ধতা',
      'card_purpose_desc': 'ভারত DPDP আইন ২০২৩ অনুযায়ী, ব্যক্তিগত তথ্য শুধুমাত্র পবিত্র ম্যাচমেকিংয়ের জন্য ব্যবহৃত হয়। সম্পূর্ণ সুরক্ষিত ও এনক্রিপ্ট করা।',
      'card_anticapture_title': 'FLAG_SECURE অ্যান্টি-ক্যাপচার শিল্ড',
      'card_anticapture_desc': 'স্ক্রিনশট এবং স্ক্রিন রেকর্ডিং হার্ডওয়্যার ডিসপ্লে পাইপলাইনে প্রতিরোধ করা হয়।',
      'card_rhythm_title': '১০-সোয়াইপ দৈনিক সচেতন ছন্দ',
      'card_rhythm_desc': 'মানসিক ভারসাম্য রক্ষা করতে দৈনিক অন্বেষণ ১০টি প্রোফাইলে সীমাবদ্ধ।',
    },
    'Telugu': {
      'header_title': 'UR-Heart అభయారణ్యానికి స్వాగతం',
      'header_subtitle': 'డిజిటల్ గోప్యత, సచేతన సంబంధాలు మరియు వ్యక్తిగత సార్వభౌమత్వాన్ని గౌరవించే పవిత్ర వేదిక.',
      'card_purpose_title': 'DPDP సెక్షన్ 6 ఉద్దేశ్య పరిమితి',
      'card_purpose_desc': 'భారత DPDP చట్టం 2023 ప్రకారం, వ్యక్తిగత డేటా కేవలం సమ్మతితో కూడిన మ్యాచ్‌మేకింగ్ కొరకు మాత్రమే ప్రాసెస్ చేయబడుతుంది.',
      'card_anticapture_title': 'FLAG_SECURE యాంటీ-క్యాప్చర్ షీల్డ్',
      'card_anticapture_desc': 'స్క్రీన్‌షాట్‌లు మరియు రికార్డింగ్‌లు హార్డ్‌వేర్ స్థాయిలో నిరోధించబడతాయి.',
      'card_rhythm_title': 'రోజుకు 10-స్వైప్ పరిమితి',
      'card_rhythm_desc': 'మానసిక ప్రశాంతత కొరకు రోజువారీ అన్వేషణ 10 ప్రొఫైల్‌లకు మాత్రమే పరిమితం చేయబడింది.',
    },
    'Marathi': {
      'header_title': 'UR-Heart अभयारण्यात आपले स्वागत आहे',
      'header_subtitle': 'डिजिटल गोपनीयता आणि वैयक्तिक सार्वभौमत्वाचा आदर करणारी पवित्र जागा.',
      'card_purpose_title': 'DPDP कलम 6 हेतू मर्यादा',
      'card_purpose_desc': 'भारत DPDP कायदा 2023 अंतर्गत, वैयक्तिक डेटा केवळ सहमतीने जोडीदारांच्या शोधासाठी वापरला जातो.',
      'card_anticapture_title': 'FLAG_SECURE स्क्रीन संरक्षण',
      'card_anticapture_desc': 'स्क्रीनशॉट आणि स्क्रीन रेकॉर्डिंग हार्डवेअर स्तरावर ब्लॉक केले जातात.',
      'card_rhythm_title': '10-स्वाइप दैनिक मर्यादा',
      'card_rhythm_desc': 'मानसिक आरोग्यासाठी दररोज फक्त 10 प्रोफाइल तपासण्याची मर्यादा आहे.',
    },
    'Tamil': {
      'header_title': 'UR-Heart சரணாலயத்திற்கு வரவேற்கிறோம்',
      'header_subtitle': 'டிஜிட்டல் தனியுரிமை மற்றும் தனிநபர் இறையாண்மையை மதிக்கும் புனித தளம்.',
      'card_purpose_title': 'DPDP பிரிவு 6 நோக்க வரம்பு',
      'card_purpose_desc': 'இந்திய DPDP சட்டம் 2023-ன் கீழ், தனிப்பட்ட தரவு பொருத்தங்களுக்காக மட்டுமே பயன்படுத்தப்படுகிறது.',
      'card_anticapture_title': 'FLAG_SECURE திரை பாதுகாப்பு',
      'card_anticapture_desc': 'ஸ்கிரீன்ஷாட்கள் மற்றும் பதிவுகள் வன்பொருள் மட்டத்தில் தடுக்கப்படுகின்றன.',
      'card_rhythm_title': '10-ஸ்வைப் தினசரி வரம்பு',
      'card_rhythm_desc': 'மன அமைதியைப் பாதுகாக்க தினசரி ஆய்வு 10 சுயவிவரங்களாக வரம்பிடப்பட்டுள்ளது.',
    },
    'Gujarati': {
      'header_title': 'UR-Heart અભયારણ્યમાં આપનું સ્વાગત છે',
      'header_subtitle': 'ડિજિટલ ગોપનીયતા અને માનસિક સાર્વભૌમત્વનું સન્માન કરતું પવિત્ર સ્થળ.',
      'card_purpose_title': 'DPDP કલમ 6 હેતુ મર્યાદા',
      'card_purpose_desc': 'ભારત DPDP કાયદા 2023 હેઠળ વ્યક્તિગત ડેટા માત્ર મેચમેકિંગ માટે ઉપયોગમાં લેવાય છે.',
      'card_anticapture_title': 'FLAG_SECURE સ્ક્રીન સુરક્ષા',
      'card_anticapture_desc': 'સ્ક્રીનશોટ અને રેકોર્ડિંગ હાર્ડવેર સ્તરે અવરોધિત છે.',
      'card_rhythm_title': 'દૈનિક 10-સ્વાઇપ મર્યાદા',
      'card_rhythm_desc': 'માનસિક શાંતિ માટે દૈનિક પ્રોફાઇલ શોધ 10 સુધી મર્યાદિત છે.',
    },
    'Kannada': {
      'header_title': 'UR-Heart ಅಭಯಾರಣ್ಯಕ್ಕೆ ಸುಸ್ವಾಗತ',
      'header_subtitle': 'ಡಿಜಿಟಲ್ ಗೌಪ್ಯತೆ ಮತ್ತು ಸಾರ್ವಭೌಮತ್ವವನ್ನು ಗೌರವಿಸುವ ಪವಿತ್ರ ತಾಣ.',
      'card_purpose_title': 'DPDP ಸೆಕ್ಷನ್ 6 ಉದ್ದೇಶ ಮಿತಿ',
      'card_purpose_desc': 'ಭಾರತ DPDP ಕಾಯ್ದೆ 2023 ರ ಅಡಿಯಲ್ಲಿ ಡೇಟಾವನ್ನು ಹೊಂದಾಣಿಕೆಗೆ ಮಾತ್ರ ಬಳಸಲಾಗುತ್ತದೆ.',
      'card_anticapture_title': 'FLAG_SECURE ಸ್ಕ್ರೀನ್ ರಕ್ಷಣೆ',
      'card_anticapture_desc': 'ಸ್ಕ್ರೀನ್‌ಶಾಟ್‌ಗಳನ್ನು ಹಾರ್ಡ್‌ವೇರ್ ಮಟ್ಟದಲ್ಲಿ ನಿರ್ಬಂಧಿಸಲಾಗಿದೆ.',
      'card_rhythm_title': 'ದೈನಂದಿನ 10-ಸ್ವೈಪ್ ಮಿತಿ',
      'card_rhythm_desc': 'ದೈನಂದಿನ ಹುಡುಕಾಟವನ್ನು 10 ಪ್ರೊಫೈಲ್‌ಗಳಿಗೆ ಸೀಮಿತಗೊಳಿಸಲಾಗಿದೆ.',
    },
    'Malayalam': {
      'header_title': 'UR-Heart സാങ്ച്വറിയിലേക്ക് സ്വാഗതം',
      'header_subtitle': 'ഡിജിറ്റൽ സ്വകാര്യതയെയും പരമാധികാരത്തെയും മാനിക്കുന്ന പവിത്രമായ ഇടം.',
      'card_purpose_title': 'DPDP സെക്ഷൻ 6 ഉദ്ദേശ്യ പരിമിതി',
      'card_purpose_desc': 'ഇന്ത്യൻ DPDP ആക്റ്റ് 2023 പ്രകാരം ഡാറ്റ മാച്ച്മേക്കിംഗിനായി മാത്രം ഉപയോഗിക്കുന്നു.',
      'card_anticapture_title': 'FLAG_SECURE സ്ക്രീൻ സുരക്ഷ',
      'card_anticapture_desc': 'സ്ക്രീൻഷോട്ടുകൾ തടയപ്പെടുന്നു.',
      'card_rhythm_title': 'പ്രതിദിന 10-സ്വൈപ്പ് പരിധി',
      'card_rhythm_desc': 'പ്രതിദിന തിരച്ചിൽ 10 പ്രൊഫൈലുകളായി പരിമിതപ്പെടുത്തിയിരിക്കുന്നു.',
    },
    'Odia': {
      'header_title': 'UR-Heart ଅଭୟାରଣ୍ୟକୁ ସ୍ୱାଗତ',
      'header_subtitle': 'ଡିଜିଟାଲ୍ ଗୋପନୀୟତା ସମ୍ମାନ ଜଣାଉଥିବା ଏକ ପବିତ୍ର ସ୍ଥାନ।',
      'card_purpose_title': 'DPDP ଧାରା 6 ଉଦ୍ଦେଶ୍ୟ ସୀମା',
      'card_purpose_desc': 'ଭାରତ DPDP ଆଇନ 2023 ଅନୁଯାୟୀ ବ୍ୟକ୍ତିଗତ ତଥ୍ୟ ସୁରକ୍ଷିତ।',
      'card_anticapture_title': 'FLAG_SECURE ସ୍କ୍ରିନ୍ ସୁରକ୍ଷା',
      'card_anticapture_desc': 'ସ୍କ୍ରିନଶଟ୍ ବନ୍ଦ କରାଯାଇଛି।',
      'card_rhythm_title': 'ଦୈନିକ 10-ସ୍ୱାଇପ୍ ସୀମା',
      'card_rhythm_desc': 'ଦୈନିକ ଅନୁସନ୍ଧାନ 10ଟି ପ୍ରୋଫାଇଲ୍ ମଧ୍ୟରେ ସୀମିତ।',
    },
    'Punjabi': {
      'header_title': 'UR-Heart ਸੈੰਕਚੂਰੀ ਵਿੱਚ ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ',
      'header_subtitle': 'ਡਿਜੀਟਲ ਗੋਪਨੀਯਤਾ ਅਤੇ ਮਾਨਸਿਕ ਸ਼ਾਂਤੀ ਦਾ ਸਤਿਕਾਰ ਕਰਨ ਵਾਲਾ ਇੱਕ ਪਵਿੱਤਰ ਸਥਾਨ।',
      'card_purpose_title': 'DPDP ਧਾਰਾ 6 ਉਦੇਸ਼ ਸੀਮਾ',
      'card_purpose_desc': 'ਭਾਰਤ DPDP ਐਕਟ 2023 ਦੇ ਤਹਿਤ ਨਿੱਜੀ ਜਾਣਕਾਰੀ ਸਿਰਫ਼ ਮੈਚਮੇਕਿੰਗ ਲਈ ਵਰਤੀ ਜਾਂਦੀ ਹੈ।',
      'card_anticapture_title': 'FLAG_SECURE ਸਕ੍ਰੀਨ ਸੁਰੱਖਿਆ',
      'card_anticapture_desc': 'ਸਕ੍ਰੀਨਸ਼ੌਟ ਹਾਰਡਵੇਅਰ ਪੱਧਰ ਤੇ ਰੋਕੇ ਗਏ ਹਨ।',
      'card_rhythm_title': 'ਰੋਜ਼ਾਨਾ 10-ਸਵਾਈਪ ਸੀਮਾ',
      'card_rhythm_desc': 'ਰੋਜ਼ਾਨਾ ਖੋਜ 10 ਪ੍ਰੋਫਾਈਲਾਂ ਤੱਕ ਸੀਮਤ ਹੈ।',
    },
  };

  bool get _allConsentsAffirmed =>
      _consentPurposeLimitation && _consentAntiCapture && _consentRhythmAllowance;

  void _showLanguageSelector(BuildContext context, SanctuaryGlassTokens tokens) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: tokens.backgroundCanvas,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (ctx) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Text(
                  'Select Language (Eighth Schedule)',
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: tokens.textPrimary,
                  ),
                ),
              ),
              const Divider(height: 1),
              Flexible(
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: _eighthScheduleLanguages.length,
                  itemBuilder: (context, i) {
                    final lang = _eighthScheduleLanguages[i];
                    final isSelected = lang['name'] == _selectedLanguage;
                    return ListTile(
                      title: Text(
                        '${lang['name']} (${lang['native']})',
                        style: TextStyle(
                          color: isSelected ? SanctuaryGlassTokens.brandSacredGold : tokens.textPrimary,
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                      trailing: isSelected ? const Icon(Icons.check, color: SanctuaryGlassTokens.brandSacredGold) : null,
                      onTap: () {
                        setState(() => _selectedLanguage = lang['name']!);
                        Navigator.pop(ctx);
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _handleConsentAffirmation(BuildContext context) async {
    final purpose = _consentPurposeLimitation;
    final antiCapture = _consentAntiCapture;
    final rhythm = _consentRhythmAllowance;

    if (!purpose || !antiCapture || !rhythm) return;

    try {
      final prefs = await SharedPreferences.getInstance();
      final record = jsonEncode({
        'version': '1.0',
        'timestamp': DateTime.now().toUtc().toIso8601String(),
        'language': _selectedLanguage,
        'purpose_limitation': purpose,
        'flag_secure_anti_capture': antiCapture,
        'rhythm_10_swipe': rhythm,
      });
      final saved = await prefs.setString(ConsentScreen.consentRecordKey, record);
      if (!saved) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Failed to persist statutory consent. Please try again.'),
            ),
          );
        }
        return;
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error saving consent: $e'),
          ),
        );
      }
      return;
    }

    if (context.mounted) {
      context.go('/auth');
    }
  }

  void _toggleAll(bool value) {
    setState(() {
      _consentPurposeLimitation = value;
      _consentAntiCapture = value;
      _consentRhythmAllowance = value;
    });
  }

  @override
  Widget build(BuildContext context) {
    final themeState = ref.watch(themeProvider);
    final isDark = themeState.isDark;
    final tokens = isDark ? SanctuaryGlassTokens.dark() : SanctuaryGlassTokens.light();

    final localized = _localizedStrings[_selectedLanguage] ?? _localizedStrings['English']!;

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
                    const Color(0xFFF0EAE1),
                    const Color(0xFFF9F6F0),
                  ],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Top Bar: Semantic identifier + Language Selector + Theme Toggle Pill
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 8.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Semantics(
                      label: 'ConsentScreen',
                      child: Text(
                        'ConsentScreen',
                        style: TextStyle(
                          fontSize: 10,
                          color: tokens.textTertiary.withValues(alpha: 0.5),
                          fontFamily: SanctuaryTypography.sansFont,
                        ),
                      ),
                    ),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Language Selector Pill (DPDP Act Section 6(7) Multi-Lingual Notice)
                        SanctuaryGlassContainer(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          borderRadius: 20,
                          blurSigma: 8.0,
                          onTap: () => _showLanguageSelector(context, tokens),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(
                                Icons.language_rounded,
                                size: 15,
                                color: SanctuaryGlassTokens.brandSacredGold,
                              ),
                              const SizedBox(width: 5),
                              Text(
                                _selectedLanguage,
                                style: TextStyle(
                                  fontFamily: SanctuaryTypography.sansFont,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w500,
                                  color: tokens.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        // Theme Toggle Pill
                        SanctuaryGlassContainer(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          borderRadius: 20,
                          blurSigma: 8.0,
                          onTap: () => ref.read(themeProvider.notifier).toggleTheme(),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                isDark ? Icons.dark_mode_rounded : Icons.light_mode_rounded,
                                size: 16,
                                color: SanctuaryGlassTokens.brandSacredGold,
                              ),
                              const SizedBox(width: 6),
                              Text(
                                isDark ? 'Dark Sanctuary' : 'Light Sanctuary',
                                style: TextStyle(
                                  fontFamily: SanctuaryTypography.sansFont,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w500,
                                  color: tokens.textPrimary,
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

              // Editorial Header
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 16),
                child: Column(
                  children: [
                    Text(
                      localized['header_title']!,
                      style: SanctuaryTypography.titleH1(tokens.textPrimary, isDark: isDark),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      localized['header_subtitle']!,
                      style: TextStyle(
                        fontFamily: SanctuaryTypography.sansFont,
                        fontSize: 13,
                        height: 1.4,
                        color: tokens.textSecondary,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),

              // Quick "Affirm All" Toggle
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 4.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    GestureDetector(
                      onTap: () => _toggleAll(!_allConsentsAffirmed),
                      child: Text(
                        _allConsentsAffirmed ? 'Deselect All' : 'Affirm All Clauses',
                        style: const TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: SanctuaryGlassTokens.brandSacredGold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // 3 Scrollable Frosted Consent Cards
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 8.0),
                  children: [
                    _buildConsentCard(
                      tokens: tokens,
                      isDark: isDark,
                      icon: Icons.verified_user_outlined,
                      iconColor: SanctuaryGlassTokens.brandSacredGold,
                      title: localized['card_purpose_title']!,
                      subtitle: localized['card_purpose_desc']!,
                      value: _consentPurposeLimitation,
                      onChanged: (v) => setState(() => _consentPurposeLimitation = v ?? false),
                    ),
                    const SizedBox(height: 14),
                    _buildConsentCard(
                      tokens: tokens,
                      isDark: isDark,
                      icon: Icons.no_photography_outlined,
                      iconColor: SanctuaryGlassTokens.brandTerracotta,
                      title: localized['card_anticapture_title']!,
                      subtitle: localized['card_anticapture_desc']!,
                      value: _consentAntiCapture,
                      onChanged: (v) => setState(() => _consentAntiCapture = v ?? false),
                    ),
                    const SizedBox(height: 14),
                    _buildConsentCard(
                      tokens: tokens,
                      isDark: isDark,
                      icon: Icons.hourglass_empty_rounded,
                      iconColor: SanctuaryGlassTokens.brandPine,
                      title: localized['card_rhythm_title']!,
                      subtitle: localized['card_rhythm_desc']!,
                      value: _consentRhythmAllowance,
                      onChanged: (v) => setState(() => _consentRhythmAllowance = v ?? false),
                    ),
                    const SizedBox(height: 20),
                  ],
                ),
              ),

              // Affirm & Enter CTA Button
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 8, 24, 20),
                child: Opacity(
                  opacity: _allConsentsAffirmed ? 1.0 : 0.45,
                  child: SanctuaryGlassContainer(
                    width: double.infinity,
                    height: 56,
                    borderRadius: 16,
                    blurSigma: 16.0,
                    customBorderGradient: _allConsentsAffirmed
                        ? const LinearGradient(
                            colors: [
                              SanctuaryGlassTokens.brandSacredGold,
                              SanctuaryGlassTokens.brandTerracottaGlow,
                            ],
                          )
                        : null,
                    customTint: _allConsentsAffirmed
                        ? SanctuaryGlassTokens.brandSacredGold.withValues(alpha: 0.15)
                        : null,
                    onTap: _allConsentsAffirmed ? () => _handleConsentAffirmation(context) : null,
                    child: Center(
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.check_circle_outline_rounded,
                            size: 18,
                            color: _allConsentsAffirmed
                                ? SanctuaryGlassTokens.brandSacredGold
                                : tokens.textTertiary,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'I Affirm & Enter the Sanctuary',
                            style: TextStyle(
                              fontFamily: SanctuaryTypography.sansFont,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              letterSpacing: 0.2,
                              color: _allConsentsAffirmed
                                 ? tokens.textPrimary
                                  : tokens.textTertiary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildConsentCard({
    required SanctuaryGlassTokens tokens,
    required bool isDark,
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool?> onChanged,
  }) {
    return SanctuaryGlassContainer(
      blurSigma: 12.0,
      borderRadius: 16.0,
      padding: const EdgeInsets.all(16.0),
      customBorderGradient: value
          ? LinearGradient(
              colors: [
                iconColor.withValues(alpha: 0.8),
                iconColor.withValues(alpha: 0.2),
              ],
            )
          : null,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Checkbox(
            value: value,
            activeColor: iconColor,
            checkColor: Colors.white,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
            onChanged: onChanged,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(icon, size: 18, color: iconColor),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        title,
                        style: TextStyle(
                          fontFamily: SanctuaryTypography.sansFont,
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: tokens.textPrimary,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  subtitle,
                  style: TextStyle(
                    fontFamily: SanctuaryTypography.sansFont,
                    fontSize: 12,
                    height: 1.4,
                    color: tokens.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
