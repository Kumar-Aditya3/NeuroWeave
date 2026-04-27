package dev.neuroweave.watcher

import android.app.AppOpsManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.app.Activity
import android.os.Bundle
import android.provider.Settings
import android.view.ViewGroup
import android.widget.Button
import android.widget.CheckBox
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var store: SettingsStore
    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        store = SettingsStore(this)
        handleShareIntent(intent)
        render()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleShareIntent(intent)
    }

    private fun render() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }

        fun field(label: String, value: String): EditText {
            root.addView(TextView(this).apply { text = label })
            return EditText(this).apply {
                setText(value)
                layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                root.addView(this)
            }
        }

        val userId = field("User ID", store.userId)
        val clientName = field("Device name", store.clientName)
        val ingestUrl = field("Ingest URL", store.ingestUrl)
        val ingestKey = field("Ingest key", store.ingestKey)
        val headerName = field("Auth header", store.headerName)
        val enabled = CheckBox(this).apply {
            text = "Watch foreground apps"
            isChecked = store.watcherEnabled
            root.addView(this)
        }

        status = TextView(this).apply {
            text = if (hasUsageAccess()) "Usage access granted" else "Usage access needed"
            root.addView(this)
        }

        root.addView(Button(this).apply {
            text = "Save"
            setOnClickListener {
                store.userId = userId.text.toString()
                store.clientName = clientName.text.toString()
                store.ingestUrl = ingestUrl.text.toString()
                store.ingestKey = ingestKey.text.toString()
                store.headerName = headerName.text.toString()
                store.watcherEnabled = enabled.isChecked
                if (enabled.isChecked) startWatcher() else stopWatcher()
                status.text = "Saved"
            }
        })

        root.addView(Button(this).apply {
            text = "Open Usage Access"
            setOnClickListener {
                startActivity(Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS))
            }
        })

        root.addView(Button(this).apply {
            text = "Send Test Event"
            setOnClickListener {
                Thread {
                    val ok = EventSender(store).send(
                        ActivityEvent(
                            userId = store.userId,
                            deviceId = store.deviceId,
                            clientName = store.clientName,
                            source = "mobile_share",
                            eventType = "mobile_share",
                            title = "Android watcher test",
                            category = "mobile_share",
                            contentText = "manual smoke test from Android watcher",
                            durationSeconds = 1,
                        )
                    )
                    runOnUiThread { status.text = if (ok) "Test event sent" else "Test event failed" }
                }.start()
            }
        })

        setContentView(root)
        if (store.watcherEnabled) startWatcher()
    }

    private fun handleShareIntent(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT).orEmpty()
        val subject = intent.getStringExtra(Intent.EXTRA_SUBJECT).orEmpty()
        if (sharedText.isBlank() && subject.isBlank()) return

        Thread {
            EventSender(store).send(
                ActivityEvent(
                    userId = store.userId,
                    deviceId = store.deviceId,
                    clientName = store.clientName,
                    source = "mobile_share",
                    eventType = "mobile_share",
                    title = subject.ifBlank { sharedText.take(80).ifBlank { "Shared from Android" } },
                    url = extractUrl(sharedText),
                    category = "mobile_share",
                    contentText = sharedText,
                )
            )
        }.start()
    }

    private fun extractUrl(text: String): String? {
        val match = Regex("""https?://\S+""").find(text) ?: return null
        return match.value.trimEnd('.', ',', ')')
    }

    private fun startWatcher() {
        if (!hasUsageAccess()) return
        val intent = Intent(this, UsageWatcherService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent) else startService(intent)
    }

    private fun stopWatcher() {
        stopService(Intent(this, UsageWatcherService::class.java))
    }

    private fun hasUsageAccess(): Boolean {
        val appOps = getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = appOps.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, android.os.Process.myUid(), packageName)
        return mode == AppOpsManager.MODE_ALLOWED
    }
}
