"""OAM sprite — a Tile that can be positioned anywhere on screen."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .tile import Tile


class Sprite:
    """A movable 8×8 (or 8×16) object rendered on top of the background.

    Attributes
    ----------
    tile      : Tile to draw. For 8×16 mode, provide a second tile via tile_b.
    x, y      : Screen position in pixels.
    visible   : Whether to draw this sprite.
    flip_x    : Mirror horizontally.
    flip_y    : Mirror vertically.
    palette   : 0 or 1 — selects OBP0 or OBP1 palette.
    priority  : If True, sprite renders behind BG colors 1–3.
    """

    def __init__(
        self,
        tile: "Tile",
        x: int = 0,
        y: int = 0,
        *,
        tile_b: Optional["Tile"] = None,
        visible: bool = True,
        flip_x: bool = False,
        flip_y: bool = False,
        palette: int = 0,
        priority: bool = False,
    ) -> None:
        """Create a sprite from a tile at screen position (x, y)."""
        self.tile = tile
        self.tile_b = tile_b          # second tile for 8×16 mode
        self.x = x
        self.y = y
        self.visible = visible
        self.flip_x = flip_x
        self.flip_y = flip_y
        self.palette = palette & 1
        self.priority = priority

    # ------------------------------------------------------------------
    # Movement helpers
    # ------------------------------------------------------------------

    def move(self, dx: int, dy: int) -> None:
        """Translate the sprite by (dx, dy) pixels."""
        self.x += dx
        self.y += dy

    def move_to(self, x: int, y: int) -> None:
        """Set the sprite's screen position to (x, y)."""
        self.x = x
        self.y = y

    def clamp(self, x0: int, y0: int, x1: int, y1: int) -> None:
        """Keep sprite inside the given pixel bounds."""
        self.x = max(x0, min(x1, self.x))
        self.y = max(y0, min(y1, self.y))

    # ------------------------------------------------------------------
    # Collision
    # ------------------------------------------------------------------

    @property
    def width(self) -> int:
        """Return sprite width in pixels (taken from the tile's size)."""
        return self.tile.size

    @property
    def height(self) -> int:
        """Return sprite height in pixels; doubled when tile_b is set."""
        return self.tile.size * 2 if self.tile_b is not None else self.tile.size

    def collides_with(self, other: "Sprite") -> bool:
        """Return True if this sprite's bounding box overlaps another sprite's."""
        return (
            self.x < other.x + other.width
            and self.x + self.width > other.x
            and self.y < other.y + other.height
            and self.y + self.height > other.y
        )

    def on_screen(self, margin: int = 0) -> bool:
        """Return True if any part of the sprite is within (or within *margin* of) the screen."""
        from .constants import SCREEN_WIDTH, SCREEN_HEIGHT
        return (
            self.x + self.width + margin > 0
            and self.x - margin < SCREEN_WIDTH
            and self.y + self.height + margin > 0
            and self.y - margin < SCREEN_HEIGHT
        )

    # ------------------------------------------------------------------
    # Flip toggle helpers
    # ------------------------------------------------------------------

    def toggle_flip_x(self) -> None:
        """Toggle horizontal flip."""
        self.flip_x = not self.flip_x

    def toggle_flip_y(self) -> None:
        """Toggle vertical flip."""
        self.flip_y = not self.flip_y

    def __repr__(self) -> str:
        return f"Sprite(x={self.x}, y={self.y}, visible={self.visible})"
