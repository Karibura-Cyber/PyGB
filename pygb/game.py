"""GameBoy — the main class that ties all subsystems together."""

from __future__ import annotations
import sys
from typing import Callable, List, Optional, TYPE_CHECKING

from .color import DEFAULT as DEFAULT_PALETTE
from .graphics import Graphics
from .input import Input
from .audio import Audio
from .sprite import Sprite
from .spritegroup import SpriteGroup
from .tile import Tile

if TYPE_CHECKING:
    from .tilemap import TileMap


class GameBoy:
    """Game Boy-style game engine.

    Usage::

        gb = GameBoy(title="My Game")

        @gb.on_start
        def init():
            ...

        @gb.on_update
        def update():
            ...

        gb.run()
    """

    def __init__(
        self,
        title: str = "PyGB",
        scale: int = 3,
        fps: int = 60,
        palette=None,
        width: int = 160,
        height: int = 144,
        tile_size: int = 8,
    ) -> None:
        """Configure the window title, pixel scale, target FPS, 4-color palette, and viewport size.

        width/height set the viewport in pixels (default 160×144 — classic Game Boy).
        The physical window is width*scale × height*scale.
        tile_size controls the grid unit used for tilemaps (default 8).
        """
        self.title     = title
        self.scale     = max(1, scale)
        self.fps       = fps
        self.palette   = palette or DEFAULT_PALETTE
        self.width     = width
        self.height    = height
        self.tile_size = tile_size

        self.graphics = Graphics()
        self.input    = Input()
        self.audio    = Audio()
        self.sprites: List[Sprite] = []

        self._update_cb:  Optional[Callable] = None
        self._draw_cb:    Optional[Callable] = None
        self._start_cb:   Optional[Callable] = None
        self._stop_cb:    Optional[Callable] = None

        self._frame   = 0
        self._running = False

        # Tile surface cache: (id(tile), pal_tuple, flip_x, flip_y, transparent_color) → Surface
        self._tile_cache: dict = {}

        # Exposed after run() is called
        self._screen      = None
        self._gb_surface  = None
        self._clock       = None

    # ------------------------------------------------------------------
    # Decorator hooks
    # ------------------------------------------------------------------

    def on_start(self, fn: Callable) -> Callable:
        """Register a callback to run once before the game loop starts."""
        self._start_cb = fn
        return fn

    def on_update(self, fn: Callable) -> Callable:
        """Register a per-frame logic callback; called every frame before rendering."""
        self._update_cb = fn
        return fn

    def on_draw(self, fn: Callable) -> Callable:
        """Register a per-frame drawing callback called after the automatic render pass."""
        self._draw_cb = fn
        return fn

    def on_stop(self, fn: Callable) -> Callable:
        """Register a callback to run once when the game exits."""
        self._stop_cb = fn
        return fn

    # ------------------------------------------------------------------
    # Sprite factory
    # ------------------------------------------------------------------

    def create_sprite(
        self,
        tile: Tile,
        x: int = 0,
        y: int = 0,
        **kwargs,
    ) -> Sprite:
        """Create and register a sprite."""
        s = Sprite(tile, x, y, **kwargs)
        self.sprites.append(s)
        return s

    def create_group(
        self,
        x: int = 0,
        y: int = 0,
        **kwargs,
    ) -> SpriteGroup:
        """Create a SpriteGroup (sprite + named animations) at position (x, y)."""
        return SpriteGroup(self, x=x, y=y, **kwargs)

    def remove_sprite(self, sprite: Sprite) -> None:
        """Remove a sprite from the render list; silently ignored if not present."""
        try:
            self.sprites.remove(sprite)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Screen helpers
    # ------------------------------------------------------------------

    def fill_screen(self, color: int) -> None:
        """Fill the entire viewport surface with a single GB color index (0–3)."""
        if self._gb_surface:
            rgb = self.palette[color & 3]
            self._gb_surface.fill(rgb)

    def draw_pixel(self, x: int, y: int, color: int) -> None:
        """Plot a single pixel at (x, y) using a GB color index (0–3)."""
        if self._gb_surface and 0 <= x < self.width and 0 <= y < self.height:
            self._gb_surface.set_at((x, y), self.palette[color & 3])

    def draw_tile(self, tile: Tile, x: int, y: int, flip_x: bool = False, flip_y: bool = False) -> None:
        """Draw a tile directly to the screen at pixel (x, y), bypassing the TileMap."""
        self._blit_tile(tile, x, y, self.graphics.bg_palette, flip_x=flip_x, flip_y=flip_y)

    def draw_rect(self, x: int, y: int, w: int, h: int, color: int) -> None:
        """Draw a filled rectangle using a GB color index (0–3)."""
        if self._gb_surface:
            import pygame
            rgb = self.palette[color & 3]
            pygame.draw.rect(self._gb_surface, rgb, (x, y, w, h))

    def draw_outline(self, x: int, y: int, w: int, h: int, color: int) -> None:
        """Draw a 1-pixel outlined (unfilled) rectangle using a GB color index (0–3)."""
        if self._gb_surface:
            import pygame
            rgb = self.palette[color & 3]
            pygame.draw.rect(self._gb_surface, rgb, (x, y, w, h), 1)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the game loop; blocks until the window is closed or quit() is called."""
        import pygame
        pygame.init()
        self.audio.init()

        self._screen = pygame.display.set_mode(
            (self.width * self.scale, self.height * self.scale)
        )
        pygame.display.set_caption(self.title)
        self._gb_surface = pygame.Surface((self.width, self.height))
        self._clock = pygame.time.Clock()

        if self._start_cb:
            self._start_cb()

        self._running = True
        while self._running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._running = False

            self.input.update(events)

            if self._update_cb:
                self._update_cb()

            self._render()

            if self._draw_cb:
                self._draw_cb()

            scaled = pygame.transform.scale(
                self._gb_surface,
                (self.width * self.scale, self.height * self.scale),
            )
            self._screen.blit(scaled, (0, 0))
            pygame.display.flip()

            self._clock.tick(self.fps)
            self._frame += 1

        if self._stop_cb:
            self._stop_cb()

        pygame.quit()

    def quit(self) -> None:
        """Signal the game loop to stop after the current frame completes."""
        self._running = False

    # ------------------------------------------------------------------
    # Internal render pass
    # ------------------------------------------------------------------

    def _render(self) -> None:
        """Composite BG layer, priority sprites, normal sprites, and Window onto the GB surface."""
        # Clear to palette color 0
        self._gb_surface.fill(self.palette[self.graphics.bg_palette[0]])

        if self.graphics.bg_enabled:
            self._render_tilemap(
                self.graphics.bg,
                self.graphics.scroll_x,
                self.graphics.scroll_y,
                self.graphics.bg_palette,
            )

        if self.graphics.sprites_enabled:
            # Priority sprites (behind BG colors 1-3) first, then normal
            for sprite in self.sprites:
                if sprite.visible and sprite.priority:
                    self._render_sprite(sprite)
            for sprite in self.sprites:
                if sprite.visible and not sprite.priority:
                    self._render_sprite(sprite)

        if self.graphics.window_enabled:
            self._render_tilemap(
                self.graphics.window,
                -self.graphics.window_x,
                -self.graphics.window_y,
                self.graphics.bg_palette,
            )

    def _render_tilemap(self, tilemap: "TileMap", scroll_x: int, scroll_y: int, pal: list) -> None:
        """Blit the visible portion of a TileMap to the GB surface, respecting scroll."""
        if not self.graphics._tiles:
            return
        ts = self.tile_size
        cols = self.width  // ts + 2
        rows = self.height // ts + 2
        for ty in range(rows):
            for tx in range(cols):
                map_tx = (tx + scroll_x // ts) % tilemap.WIDTH
                map_ty = (ty + scroll_y // ts) % tilemap.HEIGHT
                idx = tilemap.get(map_tx, map_ty)
                if 0 <= idx < len(self.graphics._tiles):
                    tile = self.graphics._tiles[idx]
                    px = tx * ts - (scroll_x % ts)
                    py = ty * ts - (scroll_y % ts)
                    self._blit_tile(tile, px, py, pal)

    def _render_sprite(self, sprite: Sprite) -> None:
        """Blit a sprite's tile (and tile_b for 8×16 mode) to the GB surface."""
        pal = (
            self.graphics.obj_palette0
            if sprite.palette == 0
            else self.graphics.obj_palette1
        )
        self._blit_tile(sprite.tile, sprite.x, sprite.y, pal,
                        flip_x=sprite.flip_x, flip_y=sprite.flip_y,
                        transparent_color=0)
        if sprite.tile_b is not None:
            self._blit_tile(sprite.tile_b, sprite.x, sprite.y + 8, pal,
                            flip_x=sprite.flip_x, flip_y=sprite.flip_y,
                            transparent_color=0)

    def _get_tile_surface(
        self,
        tile: Tile,
        pal: list,
        flip_x: bool,
        flip_y: bool,
        transparent_color: Optional[int],
    ):
        """Return a cached pygame.Surface for a tile rendered with the given palette and transforms."""
        import pygame
        key = (id(tile), tuple(pal), flip_x, flip_y, transparent_color)
        if key not in self._tile_cache:
            ts = tile.size
            surf = pygame.Surface((ts, ts))
            palette = self.palette
            for row in range(ts):
                for col in range(ts):
                    sx = (ts - 1 - col) if flip_x else col
                    sy = (ts - 1 - row) if flip_y else row
                    ci = tile.get_pixel(sx, sy)
                    surf.set_at((col, row), palette[pal[ci]])
            if transparent_color is not None:
                surf.set_colorkey(palette[pal[transparent_color]])
            self._tile_cache[key] = surf
        return self._tile_cache[key]

    def clear_tile_cache(self) -> None:
        """Discard all cached tile surfaces. Call after changing the palette or tile pixel data."""
        self._tile_cache.clear()

    def _blit_tile(
        self,
        tile: Tile,
        x: int,
        y: int,
        pal: list,
        flip_x: bool = False,
        flip_y: bool = False,
        transparent_color: Optional[int] = None,
    ) -> None:
        """Draw one 8×8 tile to the GB surface at pixel (x, y), applying palette and optional flips."""
        surf = self._get_tile_surface(tile, pal, flip_x, flip_y, transparent_color)
        self._gb_surface.blit(surf, (x, y))

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def frame(self) -> int:
        """Total number of frames elapsed since run() was called."""
        return self._frame

    @property
    def surface(self):
        """Direct access to the 160×144 pygame Surface (advanced use)."""
        return self._gb_surface

    def __repr__(self) -> str:
        return f"GameBoy(title={self.title!r}, fps={self.fps})"
