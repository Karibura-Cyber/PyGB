"""Tile-based collision map for PyGB.

A CollisionMap is a 2-D grid of solid/passable flags that mirrors a TileMap.
It lets you mark certain tiles as walls and then test whether sprites or
rectangles overlap solid cells, with optional sliding resolution.
"""

from __future__ import annotations
from typing import Iterable, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .tilemap import TileMap

class CollisionMap:
    """Grid of solid/passable flags, one cell per tile.

    Out-of-bounds cells are always treated as solid (world walls).

    Example::

        cmap = CollisionMap(32, 32)
        cmap.from_tilemap(gb.graphics.bg, solid_indices={wall_idx, brick_idx})

        # In your update loop:
        dx, dy = gb.input.direction()
        px, py = cmap.resolve(player.x, player.y, 8, 8, dx, dy)
        player.move_to(px, py)
    """

    def __init__(self, width: int = 32, height: int = 32, tile_size: int = 8) -> None:
        self.width     = width
        self.height    = height
        self.tile_size = tile_size
        self._cells: list[list[bool]] = [
            [False] * width for _ in range(height)
        ]

    # ------------------------------------------------------------------
    # Cell access
    # ------------------------------------------------------------------

    def set(self, tx: int, ty: int, solid: bool = True) -> None:
        """Mark tile cell (tx, ty) as solid or passable."""
        if 0 <= tx < self.width and 0 <= ty < self.height:
            self._cells[ty][tx] = solid

    def get(self, tx: int, ty: int) -> bool:
        """Return True if (tx, ty) is solid.  Out-of-bounds → True."""
        if tx < 0 or ty < 0 or tx >= self.width or ty >= self.height:
            return True
        return self._cells[ty][tx]

    def toggle(self, tx: int, ty: int) -> None:
        if 0 <= tx < self.width and 0 <= ty < self.height:
            self._cells[ty][tx] = not self._cells[ty][tx]

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def fill(self, solid: bool = True) -> None:
        """Set every cell to *solid*."""
        for row in self._cells:
            for x in range(self.width):
                row[x] = solid

    def fill_rect(self, tx: int, ty: int, w: int, h: int, solid: bool = True) -> None:
        """Mark a w×h rectangle of tile cells starting at (tx, ty)."""
        for dy in range(h):
            for dx in range(w):
                self.set(tx + dx, ty + dy, solid)

    def fill_border(self, solid: bool = True) -> None:
        """Mark the outermost row/column of cells as solid (world boundary)."""
        for tx in range(self.width):
            self.set(tx, 0, solid)
            self.set(tx, self.height - 1, solid)
        for ty in range(self.height):
            self.set(0, ty, solid)
            self.set(self.width - 1, ty, solid)

    def from_tilemap(
        self,
        tilemap: "TileMap",
        solid_indices: Iterable[int],
    ) -> None:
        """Build the collision map from a TileMap.

        Every cell whose tile index is in *solid_indices* is marked solid;
        all others are marked passable.

        Args:
            tilemap:       The TileMap to read tile indices from.
            solid_indices: Iterable of tile indices that count as solid walls.
        """
        solid_set: Set[int] = set(solid_indices)
        rows = min(self.height, tilemap.HEIGHT)
        cols = min(self.width,  tilemap.WIDTH)
        for ty in range(rows):
            for tx in range(cols):
                self._cells[ty][tx] = tilemap.get(tx, ty) in solid_set

    def from_grid(self, grid: list[list[int]], solid_value: int = 1) -> None:
        """Build from a 2-D list of ints.  Cells equal to *solid_value* become solid.

        Args:
            grid:        2-D list [row][col] of integer values.
            solid_value: Integer value that represents a solid tile (default 1).
        """
        for ty, row in enumerate(grid):
            if ty >= self.height:
                break
            for tx, val in enumerate(row):
                if tx >= self.width:
                    break
                self._cells[ty][tx] = (val == solid_value)

    # ------------------------------------------------------------------
    # Pixel-space queries
    # ------------------------------------------------------------------

    def solid_at(self, px: float, py: float) -> bool:
        """Return True if the pixel point (px, py) falls inside a solid cell."""
        return self.get(int(px) // self.tile_size, int(py) // self.tile_size)

    def overlaps_rect(self, x: float, y: float, w: int, h: int) -> bool:
        """Return True if *any* solid cell overlaps the given pixel rectangle.

        Args:
            x, y: Top-left pixel position.
            w, h: Width and height in pixels.
        """
        x0 = int(x)       // self.tile_size
        y0 = int(y)       // self.tile_size
        x1 = int(x + w - 1) // self.tile_size
        y1 = int(y + h - 1) // self.tile_size
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                if self.get(tx, ty):
                    return True
        return False

    def solid_sides(
        self, x: float, y: float, w: int, h: int
    ) -> Tuple[bool, bool, bool, bool]:
        """Check which sides of a pixel rectangle border solid cells.

        Returns:
            (left, right, top, bottom) — each True if that side is blocked.
        """
        cx0 = int(x)          // self.tile_size
        cx1 = int(x + w - 1)  // self.tile_size
        cy0 = int(y)          // self.tile_size
        cy1 = int(y + h - 1)  // self.tile_size
        mid_col = int(x + w // 2) // self.tile_size
        mid_row = int(y + h // 2) // self.tile_size

        left   = self.get(cx0 - 1, mid_row)
        right  = self.get(cx1 + 1, mid_row)
        top    = self.get(mid_col, cy0 - 1)
        bottom = self.get(mid_col, cy1 + 1)
        return left, right, top, bottom

    # ------------------------------------------------------------------
    # Movement resolution
    # ------------------------------------------------------------------

    def resolve(
        self,
        x: float,
        y: float,
        w: int,
        h: int,
        dx: float,
        dy: float,
    ) -> Tuple[float, float]:
        """Move a pixel rectangle by (dx, dy) and resolve collisions with solid cells.

        Axes are resolved independently (horizontal first) so the object can
        slide along walls rather than stopping dead.

        Args:
            x, y: Current top-left pixel position.
            w, h: Width and height in pixels.
            dx:   Desired horizontal displacement.
            dy:   Desired vertical displacement.

        Returns:
            (new_x, new_y) after collision resolution.
        """
        # Horizontal
        nx = x + dx
        if self.overlaps_rect(nx, y, w, h):
            ts = self.tile_size
            if dx > 0:
                nx = (int(nx + w - 1) // ts) * ts - w
            elif dx < 0:
                nx = (int(nx) // ts + 1) * ts
            else:
                nx = x

        # Vertical
        ny = y + dy
        if self.overlaps_rect(nx, ny, w, h):
            ts = self.tile_size
            if dy > 0:
                ny = (int(ny + h - 1) // ts) * ts - h
            elif dy < 0:
                ny = (int(ny) // ts + 1) * ts
            else:
                ny = y

        return nx, ny

    # ------------------------------------------------------------------
    # Debug
    # ------------------------------------------------------------------

    def debug_print(self) -> None:
        """Print the collision map to stdout using '#' for solid, '.' for open."""
        for row in self._cells:
            print("".join("#" if c else "." for c in row))

    def __repr__(self) -> str:
        solids = sum(c for row in self._cells for c in row)
        return f"CollisionMap({self.width}×{self.height}, solid={solids})"
