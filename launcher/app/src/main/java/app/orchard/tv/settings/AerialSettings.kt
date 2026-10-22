package app.orchard.tv.settings

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.core.content.edit

/**
 * How the focused app shows itself, named after tvOS's Accessibility > Increase Contrast > Focus Style.
 *
 * tvOS's standard focus relies on the Siri Remote's touch surface: the icon tilts with the thumb, and
 * that motion is what the eye follows. With the D-pad remotes these TVs ship with, the icon only
 * grows, and owners lost track of it. High Contrast adds a white frame and is the default here.
 */
enum class FocusStyle(val key: String) {
    Standard("standard"), HighContrast("high_contrast");

    companion object {
        fun of(key: String?) = entries.firstOrNull { it.key == key } ?: HighContrast
    }
}

/** Aerial's own preferences. Compose state, written on the main thread only. */
object AerialSettings {
    private const val PREFS = "settings"
    private var started = false
    private lateinit var app: Context

    var focusStyle by mutableStateOf(FocusStyle.HighContrast); private set
    var favorites by mutableStateOf(FavoriteOrder.defaults); private set
    var darkBackground by mutableStateOf(false); private set
    var castPackage by mutableStateOf<String?>(null); private set
    var diskPackage by mutableStateOf<String?>(null); private set

    /** TV inputs pinned to Home as tiles, by TvInputInfo id. */
    var pinnedSources by mutableStateOf<Set<String>>(emptySet()); private set

    /**
     * The input to open when the TV is switched on (a set-top box, an Apple TV), by TvSource id;
     * null for none. Home still comes back to Aerial. Issue #25.
     */
    var bootSource by mutableStateOf<String?>(null); private set

    fun init(context: Context) {
        if (started) return
        started = true
        app = context.applicationContext
        val prefs = app.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        focusStyle = FocusStyle.of(prefs.getString("focus_style", null))
        favorites = FavoriteOrder.normalize(prefs.getString("home_favorites", null)?.split(',') ?: FavoriteOrder.defaults)
        darkBackground = prefs.getBoolean("home_dark", false)
        castPackage = prefs.getString("cast_package", null)
        diskPackage = prefs.getString("disk_package", null)
        pinnedSources = prefs.getStringSet("pinned_sources", null)?.toSet() ?: emptySet()
        bootSource = prefs.getString("boot_source", null)
    }

    fun chooseBootSource(id: String?) {
        bootSource = id
        app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putString("boot_source", id) }
    }

    fun setPinned(inputId: String, pinned: Boolean) {
        pinnedSources = if (pinned) pinnedSources + inputId else pinnedSources - inputId
        app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putStringSet("pinned_sources", pinnedSources) }
    }


    fun chooseFocusStyle(style: FocusStyle) {
        focusStyle = style
        app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putString("focus_style", style.key) }
    }

    fun moveFavorite(key: String, delta: Int) = saveFavorites(FavoriteOrder.move(favorites, key, delta))
    fun toggleFavorite(key: String) = saveFavorites(FavoriteOrder.toggle(favorites, key))
    fun resetFavorites() = saveFavorites(FavoriteOrder.defaults)
    private fun saveFavorites(keys: List<String>) {
        favorites = keys
        app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putString("home_favorites", keys.joinToString(",")) }
    }
    fun chooseDarkBackground(dark: Boolean) {
        darkBackground = dark
        app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putBoolean("home_dark", dark) }
    }
    fun chooseShortcut(cast: Boolean, key: String?) {
        if (cast) castPackage = key else diskPackage = key
        app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit { putString(if (cast) "cast_package" else "disk_package", key) }
    }
}
