package app.orchard.tv.settings

/** Package keys only: custom channel builds can be chosen from the installed-app library. */
object FavoriteOrder {
    const val LIMIT = 12
    val defaults = listOf("com.ktcp.video", "com.gitvdemo.video", "com.cibn.tv",
        "com.hunantv.license", "com.xiaodianshi.tv.yst", "com.netflix.ninja",
        "com.google.android.youtube.tv")
    private val packageKey = Regex("[A-Za-z_][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+")

    fun normalize(keys: List<String>): List<String> = keys.filter { packageKey.matches(it) }
        .distinct().take(LIMIT).ifEmpty { defaults }

    fun move(keys: List<String>, key: String, delta: Int): List<String> {
        val list = normalize(keys).toMutableList()
        val from = list.indexOf(key)
        if (from < 0) return list
        val to = (from + delta.coerceIn(-1, 1)).coerceIn(0, list.lastIndex)
        list.removeAt(from)
        list.add(to, key)
        return list
    }

    fun toggle(keys: List<String>, key: String): List<String> {
        val list = normalize(keys)
        if (!packageKey.matches(key)) return list
        return when {
            key in list -> if (list.size > 1) list - key else list
            list.size < LIMIT -> list + key
            else -> list
        }
    }
}
