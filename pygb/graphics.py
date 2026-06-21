"""Graphics subsystem — VRAM tile registry, palettes, BG/Window layers."""

from __future__ import annotations
from typing import Sequence, TYPE_CHECKING

from .tilemap import TileMap

if TYPE_CHECKING:
    from .tile import Tile


class Graphics:
    """Manages tile VRAM and the two background layers (BG + Window).

    Palette format: list of 4 ints (0–3), mapping color index → shade index.
    A palette of [0, 1, 2, 3] is identity (no remapping).
    """

    MAX_TILES = 256

    def __init__(self) -> None:
        """Initialize VRAM, BG/Window tilemaps, identity palettes, and zero scroll."""
        self._tiles: List["Tile"] = []

        # Two background layers
        self.bg     = TileMap()   # scrollable background
        self.window = TileMap()   # fixed-position window overlay (HUD, etc.)

        # Scroll registers for BG layer
        self.scroll_x: int = 0
        self.scroll_y: int = 0

        # Window position (WX is offset by 7 on real hardware)
        self.window_x: int = 0
        self.window_y: int = 0

        # Layer enable flags
        self.bg_enabled:      bool = True
        self.window_enabled:  bool = False
        self.sprites_enabled: bool = True

        # Palettes (identity by default)
        self.bg_palette:   List[int] = [0, 1, 2, 3]
        self.obj_palette0: List[int] = [0, 1, 2, 3]
        self.obj_palette1: List[int] = [0, 1, 2, 3]

    # ------------------------------------------------------------------
    # Tile registry (VRAM)
    # ------------------------------------------------------------------

    def add_tile(self, tile: "Tile") -> int:
        """Register a tile and return its index."""
        if len(self._tiles) >= self.MAX_TILES:
            raise RuntimeError("VRAM full — maximum 256 tiles")
        idx = len(self._tiles)
        self._tiles.append(tile)
        return idx

    def add_tiles(self, tiles: Sequence["Tile"]) -> int:
        """Register multiple tiles and return the index of the first one."""
        start = len(self._tiles)
        for t in tiles:
            self.add_tile(t)
        return start

    def set_tile(self, index: int, tile: "Tile") -> None:
        """Replace an existing tile in VRAM at *index*."""
        if index < 0 or index >= len(self._tiles):
            raise IndexError(f"Tile index {index} out of range")
        self._tiles[index] = tile

    def get_tile(self, index: int) -> "Tile":
        """Return the tile stored at *index* in VRAM."""
        return self._tiles[index]

    @property
    def tile_count(self) -> int:
        """Number of tiles currently registered in VRAM."""
        return len(self._tiles)

    # ------------------------------------------------------------------
    # Palette helpers
    # ------------------------------------------------------------------

    def set_bg_palette(self, mapping: Sequence[int]) -> None:
        """Set BG palette — 4-element list mapping color index → shade (0–3)."""
        self.bg_palette = list(mapping)[:4]

    def set_obj_palette(self, slot: int, mapping: Sequence[int]) -> None:
        """Set object (sprite) palette 0 or 1."""
        if slot == 0:
            self.obj_palette0 = list(mapping)[:4]
        else:
            self.obj_palette1 = list(mapping)[:4]

    # ------------------------------------------------------------------
    # Scroll helpers
    # ------------------------------------------------------------------

    def scroll(self, dx: int, dy: int) -> None:
        """Scroll the BG layer by (dx, dy) pixels."""
        self.scroll_x += dx
        self.scroll_y += dy

    def scroll_to(self, x: int, y: int) -> None:
        """Set the BG scroll position to (x, y)."""
        self.scroll_x = x
        self.scroll_y = y

    def __repr__(self) -> str:
        return (
            f"Graphics(tiles={self.tile_count}, "
            f"scroll=({self.scroll_x},{self.scroll_y}))"
        )
