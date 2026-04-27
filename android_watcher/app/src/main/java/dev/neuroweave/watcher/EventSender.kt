package dev.neuroweave.watcher

import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant

data class ActivityEvent(
    val userId: String,
    val deviceId: String,
    val clientName: String,
    val source: String,
    val eventType: String,
    val title: String,
    val url: String? = null,
    val category: String? = null,
    val contentText: String? = null,
    val processName: String? = null,
    val durationSeconds: Int? = null,
)

class EventSender(private val settings: SettingsStore) {
    fun send(event: ActivityEvent): Boolean {
        val ingestUrl = settings.ingestUrl
        if (ingestUrl.isBlank()) return false

        val payload = JSONObject()
            .put("user_id", event.userId)
            .put("device_id", event.deviceId)
            .put("client_name", event.clientName)
            .put("source", event.source)
            .put("event_type", event.eventType)
            .put("title", event.title)
            .put("timestamp", Instant.now().toString())

        event.url?.let { payload.put("url", it) }
        event.category?.let { payload.put("category", it) }
        event.contentText?.let { payload.put("content_text", it) }
        event.processName?.let { payload.put("process_name", it) }
        event.durationSeconds?.let { payload.put("duration_seconds", it) }

        return try {
            val connection = (URL(ingestUrl).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = 8000
                readTimeout = 8000
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                if (settings.ingestKey.isNotBlank()) {
                    setRequestProperty(settings.headerName, settings.ingestKey)
                }
            }
            OutputStreamWriter(connection.outputStream, Charsets.UTF_8).use { writer ->
                writer.write(payload.toString())
            }
            connection.responseCode in 200..299
        } catch (_: Exception) {
            false
        }
    }
}
