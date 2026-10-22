package app.orchard.tv.settings

import org.junit.Assert.*
import org.junit.Test

class FavoriteOrderTest {
    @Test fun rejectsMalformedConfigurationAndKeepsValidChannelPackages() {
        assertEquals(listOf("tv.channel.custom", "com.vendor.player"), FavoriteOrder.normalize(
            listOf("", "tv.channel.custom", "tv.channel.custom", "bad/path", "com.vendor.player")))
        assertEquals(FavoriteOrder.defaults, FavoriteOrder.normalize(listOf("invalid")))
    }
    @Test fun movementPreservesEveryOtherFavorite() {
        val keys = listOf("tv.a.app", "tv.b.app", "tv.c.app")
        assertEquals(listOf("tv.b.app", "tv.a.app", "tv.c.app"), FavoriteOrder.move(keys, "tv.b.app", -1))
        assertEquals(keys, FavoriteOrder.move(keys, "tv.a.app", -1))
        assertEquals(keys, FavoriteOrder.move(keys, "missing.app", 1))
    }
    @Test fun lastFavoriteAndLimitAreRespected() {
        assertEquals(listOf("tv.a.app"), FavoriteOrder.toggle(listOf("tv.a.app"), "tv.a.app"))
        val full = (1..FavoriteOrder.LIMIT).map { "tv.channel.app$it" }
        assertEquals(full, FavoriteOrder.toggle(full, "tv.extra.app"))
        assertEquals(full.drop(1), FavoriteOrder.toggle(full, full.first()))
    }
}
