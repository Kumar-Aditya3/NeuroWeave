package dev.neuroweave.watcher

object AppCategorizer {
    private val study = setOf("coursera", "udemy", "khan", "swayam", "classroom", "notion", "obsidian")
    private val media = setOf("youtube", "spotify", "netflix", "primevideo", "mxplayer", "vlc")
    private val communication = setOf("whatsapp", "discord", "telegram", "instagram", "slack", "gmail")
    private val gaming = setOf("mihoyo", "hoyoverse", "riot", "pubg", "minecraft", "roblox", "epicgames")
    private val browsing = setOf("chrome", "firefox", "opera", "browser", "edge")

    fun categoryFor(packageName: String, label: String): String {
        val haystack = "$packageName $label".lowercase()
        return when {
            study.any { haystack.contains(it) } -> "study"
            media.any { haystack.contains(it) } -> "media"
            communication.any { haystack.contains(it) } -> "communication"
            gaming.any { haystack.contains(it) } -> "gaming"
            browsing.any { haystack.contains(it) } -> "browsing"
            else -> "mobile_app"
        }
    }
}
