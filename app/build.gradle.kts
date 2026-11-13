plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val releaseKeystorePath = System.getenv("JROCAI_ANDROID_KEYSTORE_PATH")
val releaseKeystorePassword = System.getenv("JROCAI_ANDROID_KEYSTORE_PASSWORD")
val releaseKeyAlias = System.getenv("JROCAI_ANDROID_KEY_ALIAS")
val releaseKeyPassword = System.getenv("JROCAI_ANDROID_KEY_PASSWORD")
val releaseRequested = gradle.startParameter.taskNames.any {
    it.contains("assembleRelease", ignoreCase = true) ||
        it.contains("bundleRelease", ignoreCase = true)
}
if (releaseRequested && listOf(releaseKeystorePath, releaseKeystorePassword, releaseKeyAlias, releaseKeyPassword).any { it.isNullOrBlank() }) {
    throw GradleException("Release signing secrets are missing. Configure all JROCAI_ANDROID_* values in the protected build environment.")
}

android {
    namespace = "online.jrocai.phone"
    compileSdk = 35

    defaultConfig {
        applicationId = "online.jrocai.phone"
        minSdk = 26
        targetSdk = 35
        versionCode = 2
        versionName = "0.2.0"
    }

    signingConfigs {
        create("release") {
            if (!releaseKeystorePath.isNullOrBlank()) {
                storeFile = file(releaseKeystorePath)
                storePassword = releaseKeystorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            signingConfig = signingConfigs.getByName("release")
        }
    }

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
