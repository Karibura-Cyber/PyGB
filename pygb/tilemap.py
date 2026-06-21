"""Tile map — used for the Background and Window layers."""

from __future__ import annotations
from typing import List, Optional


class TileMap:
    """Grid of tile indices that wraps at its boundaries (torus topology, like real GB).

    Default size is 32×32 tiles (256×256 px). Pass width/height to the constructor
    for larger scrollable worlds.
    """

    def __init__(self, width: int = 32, height: int = 32) -> None:
        """Initialize a width×height tile map with all cells set to tile index 0."""
        self.WIDTH  = width
        self.HEIGHT = height
        self._map: List[List[int]] = [[0] * self.WIDTH for _ in range(self.HEIGHT)]

    # ------------------------------------------------------------------
    # Tile index access
    # ------------------------------------------------------------------

    def set(self, tx: int, ty: int, index: int) -> None:
        """Write tile index at (tx, ty), wrapping at map boundaries."""
        self._map[ty % self.HEIGHT][tx % self.WIDTH] = index

    def get(self, tx: int, ty: int) -> int:
        """Read tile index at (tx, ty), wrapping at map boundaries."""
        return self._map[ty % self.HEIGHT][tx % self.WIDTH]

    # Aliases that feel more natural
    def set_tile(self, tx: int, ty: int, index: int) -> None:
        """Alias for set()."""
        self.set(tx, ty, index)

    def get_tile(self, tx: int, ty: int) -> int:
        """Alias for get()."""
        return self.get(tx, ty)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def fill(self, index: int) -> None:
        """Set every cell in the map to the given tile index."""
        for row in self._map:
            for x in range(self.WIDTH):
                row[x] = index

    def fill_rect(self, tx: int, ty: int, w: int, h: int, index: int) -> None:
        """Fill a w×h rectangle of tiles starting at (tx, ty) with the given index."""
        for dy in range(h):
            for dx in range(w):
                self.set(tx + dx, ty + dy, index)

    def draw_text(self, text: str, tx: int, ty: int, font_start: int = 0) -> None:
        """Write ASCII text using tiles starting at *font_start* (index for space char).

        Tile offsets: font_start + 0 = space, +1 = '!', ... matching ASCII order
        from 0x20 (space).
        """
        for i, ch in enumerate(text):
            offset = max(0, ord(ch) - 0x20)
            self.set(tx + i, ty, font_start + offset)

    def clear(self) -> None:
        """Reset all cells to tile index 0."""
        self.fill(0)

    def __repr__(self) -> str:
        return f"TileMap(32×32)"
