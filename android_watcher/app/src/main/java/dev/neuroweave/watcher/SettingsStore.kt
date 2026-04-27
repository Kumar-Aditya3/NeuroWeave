package dev.neuroweave.watcher

import android.content.Context
import java.util.UUID

class SettingsStore(context: Context) {
    private val prefs = context.getSharedPreferences("neuroweave_settings", Context.MODE_PRIVATE)

    var userId: String
        get() = prefs.getString("user_id", "kumar") ?: "kumar"
        set(value) = prefs.edit().putString("user_id", value.ifBlank { "kumar" }).apply()

    var deviceId: String
        get() {
            val current = prefs.getString("device_id", "") ?: ""
            if (current.isNotBlank()) return current
            val generated = UUID.randomUUID().toString()
            prefs.edit().putString("device_id", generated).apply()
            return generated
        }
        set(value) = prefs.edit().putString("device_id", value).apply()

    var clientName: String
        get() = prefs.getString("client_name", "Android Phone") ?: "Android Phone"
        set(value) = prefs.edit().putString("client_name", value.ifBlank { "Android Phone" }).apply()

    var ingestUrl: String
        get() = prefs.getString("ingest_url", "") ?: ""
        set(value) = prefs.edit().putString("ingest_url", value.trim()).apply()

    var ingestKey: String
        get() = prefs.getString("ingest_key", "") ?: ""
        set(value) = prefs.edit().putString("ingest_key", value.trim()).apply()

    var headerName: String
        get() = prefs.getString("header_name", "X-Ingest-Key") ?: "X-Ingest-Key"
        set(value) = prefs.edit().putString("header_name", value.ifBlank { "X-Ingest-Key" }).apply()

    var watcherEnabled: Boolean
        get() = prefs.getBoolean("watcher_enabled", false)
        set(value) = prefs.edit().putBoolean("watcher_enabled", value).apply()

    var pollSeconds: Int
        get() = prefs.getInt("poll_seconds", 15)
        set(value) = prefs.edit().putInt("poll_seconds", value.coerceIn(5, 120)).apply()

    var minDurationSeconds: Int
        get() = prefs.getInt("min_duration_seconds", 8)
        set(value) = prefs.edit().putInt("min_duration_seconds", value.coerceIn(1, 300)).apply()
}
