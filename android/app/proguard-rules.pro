# ==============================================================================
# UR-Heart Production ProGuard & R8 Obfuscation Rules
# ==============================================================================

# Flutter Engine & Embedding Entrypoints
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }
-keep class io.flutter.embedding.** { *; }
-keep class io.flutter.plugins.GeneratedPluginRegistrant { *; }
-dontwarn com.google.android.play.core.**

# UR-Heart Application Entrypoint
-keep class com.urheart.app.MainActivity { *; }

# Flutter Secure Storage & AndroidX Security Crypto (EncryptedSharedPreferences)
-keep class androidx.security.crypto.** { *; }
-keep class com.it_nomads.fluttersecurestorage.** { *; }
-dontwarn androidx.security.crypto.**

# Google Sign-In & Google Play Services
-keep class com.google.android.gms.auth.api.signin.** { *; }
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.android.gms.**

# Firebase Messaging & Core
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**

# Kotlin Runtime & Metadata
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod
-keepclassmembers class **$WhenMappings {
    <fields>;
}

# Obfuscation & Repackaging
-repackageclasses 'com.urheart.app.obf'
-allowaccessmodification

# Optimization: Strip non-essential Android Log calls in release
-assumenosideeffects class android.util.Log {
    public static boolean isLoggable(java.lang.String, int);
    public static int v(...);
    public static int d(...);
    public static int i(...);
}
