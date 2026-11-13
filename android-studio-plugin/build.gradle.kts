plugins {
    kotlin("jvm") version "2.1.0"
    id("org.jetbrains.intellij.platform") version "2.20.1"
}

group = "online.jrocai"
version = "0.1.0"

kotlin {
    jvmToolchain(21)
}

repositories {
    mavenCentral()
    intellijPlatform {
        defaultRepositories()
    }
}

dependencies {
    intellijPlatform {
        androidStudio("2025.1.1.13")
    }
}

intellijPlatform {
    pluginConfiguration {
        id = "online.jrocai.androidstudio"
        name = "J-ROC AI Developer Tools"
        version = project.version.toString()
        description = """
            First-party J-ROC AI developer panel for Android Studio.
            Includes project guidance, safe starter templates, and build workflow instructions.
        """.trimIndent()
        ideaVersion {
            sinceBuild = "251"
        }
    }
}
