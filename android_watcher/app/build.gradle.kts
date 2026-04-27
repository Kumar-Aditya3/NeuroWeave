plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "dev.neuroweave.watcher"
    compileSdk = 35

    defaultConfig {
        applicationId = "dev.neuroweave.watcher"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
}
