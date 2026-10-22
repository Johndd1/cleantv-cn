package app.orchard.tv.ui.home

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicText
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import app.orchard.tv.R
import app.orchard.tv.apps.AppEntry
import app.orchard.tv.settings.AerialSettings
import app.orchard.tv.settings.FavoriteOrder
import app.orchard.tv.settings.FocusStyle
import app.orchard.tv.ui.theme.Glyph
import app.orchard.tv.ui.theme.Type

/** All choices take effect immediately; no phone server or system screensaver takeover. */
@Composable
fun HomeSettingsSheet(apps: List<AppEntry>, onDismiss: () -> Unit) {
    var page by remember { mutableIntStateOf(0) }
    val first = remember { FocusRequester() }
    val rowFocus = remember { mutableMapOf<String, FocusRequester>() }
    var focusTarget by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(page, AerialSettings.favorites) {
        withFrameNanos { }
        val target = if (page == 1) focusTarget?.let { rowFocus[it] } else null
        runCatching { (target ?: first).requestFocus() }
    }
    BackHandler { if (page == 0) onDismiss() else page = 0 }
    Box(Modifier.fillMaxSize().background(Color(0xff10121b)).padding(40.dp)) {
        Column {
            BasicText(stringResource(R.string.home_preferences), style = Type.LargeTitle)
            BasicText(stringResource(R.string.home_preferences_hint), style = Type.Callout,
                modifier = Modifier.padding(top = 6.dp, bottom = 16.dp))
            // A new scroll position per page; focus brings off-screen choices into view.
            key(page) {
                Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(8.dp)) {
                    when (page) {
                        0 -> {
                            MenuRow(Glyph.Grid, stringResource(R.string.home_edit_favorites), { page = 1 }, focusRequester = first)
                            MenuRow(Glyph.Cast, stringResource(R.string.home_choose_cast), { page = 2 })
                            MenuRow(Glyph.Disk, stringResource(R.string.home_choose_disk), { page = 3 })
                            MenuRow(Glyph.Photo, stringResource(if (AerialSettings.darkBackground) R.string.home_use_glow else R.string.home_use_dark),
                                { AerialSettings.chooseDarkBackground(!AerialSettings.darkBackground) })
                            MenuRow(Glyph.EyeSlash, stringResource(if (AerialSettings.focusStyle == FocusStyle.HighContrast)
                                R.string.home_use_standard_focus else R.string.home_use_high_focus), {
                                AerialSettings.chooseFocusStyle(if (AerialSettings.focusStyle == FocusStyle.HighContrast) FocusStyle.Standard else FocusStyle.HighContrast)
                            })
                            MenuRow(Glyph.Move, stringResource(R.string.home_reset_favorites), { AerialSettings.resetFavorites() })
                        }
                        1 -> {
                            MenuRow(Glyph.Grid, stringResource(R.string.home_settings_back), { page = 0 }, focusRequester = first)
                            BasicText(stringResource(R.string.home_favorites_hint, FavoriteOrder.LIMIT), style = Type.Caption,
                                modifier = Modifier.padding(vertical = 12.dp))
                            AerialSettings.favorites.forEach { pkg -> key(pkg) {
                                val label = apps.firstOrNull { it.key == pkg }?.label ?: favoriteLabel(pkg)
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    BasicText(label, style = Type.Body, modifier = Modifier.weight(1f))
                                    MenuRow(Glyph.Move, stringResource(R.string.home_move_left), {
                                        focusTarget = "$pkg:left"; AerialSettings.moveFavorite(pkg, -1)
                                    }, Modifier.width(118.dp), focusRequester = rowFocus.getOrPut("$pkg:left") { FocusRequester() })
                                    MenuRow(Glyph.Move, stringResource(R.string.home_move_right), {
                                        focusTarget = "$pkg:right"; AerialSettings.moveFavorite(pkg, 1)
                                    }, Modifier.width(118.dp), focusRequester = rowFocus.getOrPut("$pkg:right") { FocusRequester() })
                                    if (AerialSettings.favorites.size > 1) MenuRow(Glyph.EyeSlash, stringResource(R.string.home_remove), {
                                        focusTarget = null; AerialSettings.toggleFavorite(pkg)
                                    }, Modifier.width(118.dp))
                                }
                            } }
                            BasicText(stringResource(if (AerialSettings.favorites.size >= FavoriteOrder.LIMIT)
                                R.string.home_favorites_full else R.string.home_add_favorite), style = Type.Headline, modifier = Modifier.padding(vertical = 12.dp))
                            if (AerialSettings.favorites.size < FavoriteOrder.LIMIT) {
                                apps.filter { it.source == null && it.key !in AerialSettings.favorites }.forEach { app ->
                                    MenuRow(Glyph.Grid, app.label, { focusTarget = "${app.key}:left"; AerialSettings.toggleFavorite(app.key) })
                                }
                            }
                        }
                        else -> {
                            val cast = page == 2
                            val selected = if (cast) AerialSettings.castPackage else AerialSettings.diskPackage
                            MenuRow(Glyph.Grid, stringResource(R.string.home_settings_back), { page = 0 }, focusRequester = first)
                            MenuRow(Glyph.Check, stringResource(R.string.home_shortcut_auto), { AerialSettings.chooseShortcut(cast, null) },
                                trailing = if (selected == null) "✓" else null)
                            apps.filter { it.source == null }.forEach { app ->
                                MenuRow(if (cast) Glyph.Cast else Glyph.Disk, app.label, { AerialSettings.chooseShortcut(cast, app.key) },
                                    trailing = if (selected == app.key) "✓" else null)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun favoriteLabel(pkg: String): String {
    val id = when (pkg) {
        "com.ktcp.video" -> R.string.home_tencent
        "com.gitvdemo.video" -> R.string.home_iqiyi
        "com.cibn.tv" -> R.string.home_youku
        "com.hunantv.license" -> R.string.home_mango
        "com.xiaodianshi.tv.yst" -> R.string.home_bilibili
        "com.netflix.ninja" -> R.string.home_netflix
        "com.google.android.youtube.tv" -> R.string.home_youtube
        else -> null
    }
    return id?.let { stringResource(it) } ?: pkg
}

@Composable
fun LibraryActions(app: AppEntry, onFavorite: () -> Unit, onHide: () -> Unit,
    onInfo: () -> Unit, onUninstall: () -> Unit, onDismiss: () -> Unit) {
    val first = remember { FocusRequester() }
    BackHandler(onBack = onDismiss)
    LaunchedEffect(app.key) { withFrameNanos { }; runCatching { first.requestFocus() } }
    Box(Modifier.fillMaxSize().background(Color.Black.copy(.6f)), contentAlignment = Alignment.Center) {
        Column(Modifier.width(380.dp).background(Color(0xff202330), RoundedCornerShape(20.dp)).padding(24.dp)) {
            BasicText(app.label, style = Type.Headline, modifier = Modifier.padding(bottom = 10.dp))
            if (app.source == null) {
                val favorite = app.key in AerialSettings.favorites
                val canToggle = if (favorite) AerialSettings.favorites.size > 1 else AerialSettings.favorites.size < FavoriteOrder.LIMIT
                if (canToggle) MenuRow(Glyph.Grid, stringResource(if (favorite) R.string.home_remove_favorite else R.string.home_add_favorite), onFavorite, focusRequester = first)
                MenuRow(Glyph.EyeSlash, stringResource(R.string.menu_hide), onHide, focusRequester = if (canToggle) null else first)
                MenuRow(Glyph.Info, stringResource(R.string.menu_info), onInfo)
                if (app.removable) MenuRow(Glyph.Trash, stringResource(R.string.menu_uninstall), onUninstall, destructive = true)
            }
            MenuRow(Glyph.Grid, stringResource(R.string.home_settings_back), onDismiss, focusRequester = if (app.source != null) first else null)
        }
    }
}
