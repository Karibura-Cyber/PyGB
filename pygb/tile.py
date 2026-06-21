"""N×N tile — the fundamental drawing unit."""

from __future__ import annotations
from typing import List, Optional, Sequence


class Tile:
    """An N×N grid of pixel color indices (0–3).

    Index 0 is the transparent color for sprites.
    Size defaults to 8 to match classic Game Boy hardware.
    """

    SIZE = 8  # class-level default; instance .size may differ

    def __init__(
        self,
        pixels: Optional[Sequence[Sequence[int]]] = None,
        size: int = 8,
    ) -> None:
        """Create a tile.

        If *pixels* is provided its dimensions determine the tile size and the
        *size* argument is ignored.  If *pixels* is None an all-zero *size*×*size*
        grid is created.
        """
        if pixels is None:
            self.size: int = size
            self._data: List[List[int]] = [[0] * size for _ in range(size)]
        else:
            rows = len(pixels)
            cols = len(pixels[0]) if rows else 0
            if rows == 0 or cols == 0:
                raise ValueError("Tile pixels cannot be empty")
            self.size = rows
            self._data = [[int(v) & 3 for v in row] for row in pixels]

    # ------------------------------------------------------------------
    # Pixel access
    # ------------------------------------------------------------------

    def get_pixel(self, x: int, y: int) -> int:
        """Return the color index at column x, row y."""
        return self._data[y][x]

    def set_pixel(self, x: int, y: int, color: int) -> None:
        """Set the color index at column x, row y."""
        self._data[y][x] = int(color) & 3

    def fill(self, color: int) -> None:
        """Fill all pixels with a single color index."""
        c = int(color) & 3
        self._data = [[c] * self.size for _ in range(self.size)]

    # ------------------------------------------------------------------
    # Transformations (return new Tile, non-destructive)
    # ------------------------------------------------------------------

    def flip_h(self) -> "Tile":
        """Return a new Tile mirrored horizontally."""
        return Tile([row[::-1] for row in self._data])

    def flip_v(self) -> "Tile":
        """Return a new Tile mirrored vertically."""
        return Tile(self._data[::-1])

    def rotate_90(self) -> "Tile":
        """Return a new Tile rotated 90° clockwise."""
        s = self.size
        rotated = [[self._data[s - 1 - x][y] for x in range(s)] for y in range(s)]
        return Tile(rotated)

    def invert(self) -> "Tile":
        """Return a new Tile with every color index inverted (3 − value)."""
        return Tile([[3 - v for v in row] for row in self._data])

    # ------------------------------------------------------------------
    # Serialisation (Game Boy 2bpp format)
    # ------------------------------------------------------------------

    def to_2bpp(self) -> bytes:
        """Encode as 16 bytes of GB 2bpp tile data."""
        result = bytearray(16)
        for row_idx, row in enumerate(self._data):
            lo = hi = 0
            for col_idx, color in enumerate(row):
                bit = 7 - col_idx
                if color & 1:
                    lo |= (1 << bit)
                if color & 2:
                    hi |= (1 << bit)
            result[row_idx * 2]     = lo
            result[row_idx * 2 + 1] = hi
        return bytes(result)

    @classmethod
    def from_2bpp(cls, data: bytes) -> "Tile":
        """Decode 16 bytes of GB 2bpp tile data into a Tile."""
        if len(data) < 16:
            raise ValueError("2bpp tile data must be at least 16 bytes")
        pixels = []
        for row_idx in range(8):
            lo = data[row_idx * 2]
            hi = data[row_idx * 2 + 1]
            row = []
            for col_idx in range(8):
                bit = 7 - col_idx
                color = ((lo >> bit) & 1) | (((hi >> bit) & 1) << 1)
                row.append(color)
            pixels.append(row)
        return cls(pixels)

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def solid(cls, color: int, size: int = 8) -> "Tile":
        """Return a Tile filled entirely with one color index."""
        t = cls(size=size)
        t.fill(color)
        return t

    @classmethod
    def border(cls, outer: int = 3, inner: int = 0, size: int = 8) -> "Tile":
        """Return a Tile with a 1-pixel border of *outer* surrounding *inner*."""
        s = size
        pixels = [[outer if (r in (0, s - 1) or c in (0, s - 1)) else inner
                   for c in range(s)] for r in range(s)]
        return cls(pixels)

    @classmethod
    def checkerboard(cls, a: int = 0, b: int = 3, size: int = 8) -> "Tile":
        """Return a Tile with alternating *a* and *b* colors in a checkerboard pattern."""
        pixels = [[(a if (r + c) % 2 == 0 else b) for c in range(size)] for r in range(size)]
        return cls(pixels)

    def __repr__(self) -> str:
        return f"Tile({self._data!r})"
