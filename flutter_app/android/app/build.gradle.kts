plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    id("com.google.gms.google-services")
}

val utilitariaKeystore = System.getenv("UTILITARIA_KEYSTORE")?.let(::file)
val utilitariaKeystorePassword = System.getenv("UTILITARIA_KEYSTORE_PASSWORD")
val utilitariaSigningReady = utilitariaKeystore?.exists() == true && !utilitariaKeystorePassword.isNullOrBlank()
val utilitariaApiUrl = System.getenv("UTILITARIA_API_URL") ?: "https://utilitaria-api.eav-labs.com"

android {
    namespace = "com.example.utilitaria"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.example.utilitaria"
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
        buildConfigField("String", "UTILITARIA_API_URL", "\"$utilitariaApiUrl\"")
    }

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        release {
            signingConfig = if (utilitariaSigningReady) {
                signingConfigs.create("utilitariaRelease") {
                    storeFile = utilitariaKeystore
                    storePassword = utilitariaKeystorePassword
                    keyAlias = "utilitaria"
                    keyPassword = utilitariaKeystorePassword
                }
            } else {
                error("No se puede generar una release sin la firma de producción de Utilitaria")
            }
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
