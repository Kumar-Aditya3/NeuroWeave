package dev.neuroweave.watcher

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper

class UsageWatcherService : Service() {
    private lateinit var settings: SettingsStore
    private lateinit var sender: EventSender
    private val handler = Handler(Looper.getMainLooper())
    private var currentPackage: String? = null
    private var currentLabel: String = ""
    private var startedAt: Long = System.currentTimeMillis()

    private val pollTask = object : Runnable {
        override fun run() {
            pollForegroundApp()
            handler.postDelayed(this, settings.pollSeconds * 1000L)
        }
    }

    override fun onCreate() {
        super.onCreate()
        settings = SettingsStore(this)
        sender = EventSender(settings)
        startForeground(41, notification())
        handler.post(pollTask)
    }

    override fun onDestroy() {
        flushCurrent()
        handler.removeCallbacks(pollTask)
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun notification(): Notification {
        val channelId = "neuroweave_watcher"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(channelId, "NeuroWeave Watcher", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, channelId)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setContentTitle("NeuroWeave Watcher")
            .setContentText("Tracking foreground app sessions")
            .setSmallIcon(android.R.drawable.ic_menu_view)
            .build()
    }

    private fun pollForegroundApp() {
        val latest = latestForegroundPackage() ?: return
        if (currentPackage == null) {
            currentPackage = latest
            currentLabel = labelFor(latest)
            startedAt = System.currentTimeMillis()
            return
        }
        if (latest == currentPackage) return

        flushCurrent()
        currentPackage = latest
        currentLabel = labelFor(latest)
        startedAt = System.currentTimeMillis()
    }

    private fun latestForegroundPackage(): String? {
        val manager = getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val now = System.currentTimeMillis()
        val events = manager.queryEvents(now - 90_000L, now)
        val event = UsageEvents.Event()
        var latestPackage: String? = null
        var latestTime = 0L
        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            if (event.eventType == UsageEvents.Event.MOVE_TO_FOREGROUND && event.timeStamp >= latestTime) {
                latestPackage = event.packageName
                latestTime = event.timeStamp
            }
        }
        return latestPackage
    }

    private fun flushCurrent() {
        val packageName = currentPackage ?: return
        val duration = ((System.currentTimeMillis() - startedAt) / 1000L).toInt()
        if (duration < settings.minDurationSeconds) return

        val category = AppCategorizer.categoryFor(packageName, currentLabel)
        val eventType = if (category == "media") "mobile_media" else "mobile_app"
        Thread {
            sender.send(
                ActivityEvent(
                    userId = settings.userId,
                    deviceId = settings.deviceId,
                    clientName = settings.clientName,
                    source = eventType,
                    eventType = eventType,
                    title = currentLabel.ifBlank { packageName },
                    category = category,
                    contentText = "$category mobile session in ${currentLabel.ifBlank { packageName }}",
                    processName = packageName,
                    durationSeconds = duration,
                )
            )
        }.start()
    }

    private fun labelFor(packageName: String): String {
        return try {
            val info = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (_: Exception) {
            packageName
        }
    }
}
