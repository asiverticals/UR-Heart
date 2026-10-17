plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    id("com.google.gms.google-services")
}

android {
    namespace = "com.urheart.app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.urheart.app"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        // Uses the version code from pubspec.yaml. When using split APKs, 1000 * ABI_VERSION
        // is added automatically by Flutter. (https://developer.android.com/studio/build/configure-apk-splits#configure-APK-versions)
        // You can force using the value of versionCode by specifying the `-P force-version-code-ignoring-abi=true`
        // flag during build.
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        val keystoreFile = project.findProperty("MYAPP_RELEASE_STORE_FILE") as String?
        if (keystoreFile != null && file(keystoreFile).exists()) {
            create("release") {
                storeFile = file(keystoreFile)
                storePassword = project.findProperty("MYAPP_RELEASE_STORE_PASSWORD") as String?
                keyAlias = project.findProperty("MYAPP_RELEASE_KEY_ALIAS") as String?
                keyPassword = project.findProperty("MYAPP_RELEASE_KEY_PASSWORD") as String?
            }
        }
    }

    buildTypes {
        release {
            signingConfigs.findByName("release")?.let {
                signingConfig = it
            }
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    gradle.taskGraph.whenReady {
        val isReleaseArtifactTask = allTasks.any { task ->
            val name = task.name
            name.contains("Release", ignoreCase = true) &&
                (name.contains("assemble", ignoreCase = true) ||
                 name.contains("bundle", ignoreCase = true) ||
                 name.contains("package", ignoreCase = true))
        }
        if (isReleaseArtifactTask && signingConfigs.findByName("release") == null) {
            throw GradleException(
                "Release artifact task requested, but MYAPP_RELEASE_STORE_FILE is missing or does not point to an existing keystore file. Configure release signing properties before building release."
            )
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
