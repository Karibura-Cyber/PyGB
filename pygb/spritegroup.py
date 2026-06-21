"""SpriteGroup — a Sprite bundled with named Animation states.

Combines sprite positioning/rendering with automatic frame cycling so you
don't have to manage tile swapping manually each frame.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from .tile import Tile
from .sprite import Sprite

if TYPE_CHECKING:
    from .game import GameBoy


class SpriteGroup:
    """A managed sprite with one or more named animation states.

    Example::

        group = gb.create_group(x=40, y=40)
        group.add("idle", [idle_tile],                   speed=12)
        group.add("walk", [walk1, walk2, walk3, walk2],  speed=6)
        group.add("jump", [jump_tile],                   speed=1, loop=False)
        group.play("idle")

        @gb.on_update
        def update():
            dx, _ = gb.input.direction()
            group.move(dx * 2, 0)
            group.flip_x = dx < 0

            if dx != 0:
                group.play("walk")
            else:
                group.play("idle")

            group.update()   # advance animation and sync sprite tile
    """

    def __init__(
        self,
        gb: "GameBoy",
        x: int = 0,
        y: int = 0,
        *,
        visible: bool = True,
        flip_x: bool = False,
        flip_y: bool = False,
        palette: int = 0,
        priority: bool = False,
    ) -> None:
        self._gb = gb
        # Placeholder tile until first animation is added
        self.sprite = gb.create_sprite(
            Tile(),
            x=x,
            y=y,
            visible=visible,
            flip_x=flip_x,
            flip_y=flip_y,
            palette=palette,
            priority=priority,
        )
        # name → {"tiles": [...], "speed": int, "loop": bool}
        self._anims: dict[str, dict] = {}
        self._current: Optional[str] = None
        self._frame_idx: int = 0
        self._tick: int = 0
        self._done: bool = False

    # ------------------------------------------------------------------
    # Animation management
    # ------------------------------------------------------------------

    def add(
        self,
        name: str,
        tiles: list[Tile],
        speed: int = 8,
        loop: bool = True,
    ) -> "SpriteGroup":
        """Register a named animation.

        Args:
            name:  State name, e.g. ``"idle"``, ``"walk"``, ``"jump"``.
            tiles: Ordered list of Tile objects for this animation.
            speed: Frames between tile advances (lower = faster).
            loop:  If False the animation stops on the last frame.

        Returns self so calls can be chained::

            group.add("idle", [t0]).add("walk", [t1, t2], speed=4)
        """
        if not tiles:
            raise ValueError(f"Animation '{name}' needs at least one tile")
        self._anims[name] = {"tiles": tiles, "speed": max(1, speed), "loop": loop}
        if self._current is None:
            self.play(name)
        return self

    def play(self, name: str, restart: bool = False) -> None:
        """Switch to a named animation.

        If the animation is already playing, does nothing unless *restart* is True.

        Args:
            name:    Name registered with :meth:`add`.
            restart: If True, rewind the animation even if it is already active.
        """
        if name not in self._anims:
            raise KeyError(f"No animation named '{name}'")
        if name == self._current and not restart:
            return
        self._current  = name
        self._frame_idx = 0
        self._tick      = 0
        self._done      = False
        self.sprite.tile = self._anims[name]["tiles"][0]

    def update(self) -> None:
        """Advance the current animation by one frame and sync the sprite tile.

        Call this once per frame inside ``@gb.on_update``.
        """
        if self._current is None or self._done:
            return
        anim = self._anims[self._current]
        self._tick += 1
        if self._tick >= anim["speed"]:
            self._tick = 0
            self._frame_idx += 1
            n = len(anim["tiles"])
            if self._frame_idx >= n:
                if anim["loop"]:
                    self._frame_idx = 0
                else:
                    self._frame_idx = n - 1
                    self._done = True
        self.sprite.tile = anim["tiles"][self._frame_idx]

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    @property
    def current(self) -> Optional[str]:
        """Name of the currently playing animation, or None."""
        return self._current

    @property
    def done(self) -> bool:
        """True when a non-looping animation has finished its last frame."""
        return self._done

    @property
    def frame_index(self) -> int:
        """Current frame index within the active animation."""
        return self._frame_idx

    def is_playing(self, name: str) -> bool:
        """Return True if *name* is the active animation."""
        return self._current == name

    # ------------------------------------------------------------------
    # Sprite pass-through — position, visibility, collision
    # ------------------------------------------------------------------

    @property
    def x(self) -> int:
        return self.sprite.x

    @x.setter
    def x(self, value: int) -> None:
        self.sprite.x = value

    @property
    def y(self) -> int:
        return self.sprite.y

    @y.setter
    def y(self, value: int) -> None:
        self.sprite.y = value

    @property
    def visible(self) -> bool:
        return self.sprite.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self.sprite.visible = value

    @property
    def flip_x(self) -> bool:
        return self.sprite.flip_x

    @flip_x.setter
    def flip_x(self, value: bool) -> None:
        self.sprite.flip_x = value

    @property
    def flip_y(self) -> bool:
        return self.sprite.flip_y

    @flip_y.setter
    def flip_y(self, value: bool) -> None:
        self.sprite.flip_y = value

    @property
    def palette(self) -> int:
        return self.sprite.palette

    @palette.setter
    def palette(self, value: int) -> None:
        self.sprite.palette = value & 1

    def move(self, dx: int, dy: int) -> None:
        self.sprite.move(dx, dy)

    def move_to(self, x: int, y: int) -> None:
        self.sprite.move_to(x, y)

    def clamp(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self.sprite.clamp(x0, y0, x1, y1)

    def collides_with(self, other) -> bool:
        """AABB collision check against another SpriteGroup or Sprite."""
        target = other.sprite if isinstance(other, SpriteGroup) else other
        return self.sprite.collides_with(target)

    def on_screen(self, margin: int = 0) -> bool:
        return self.sprite.on_screen(margin)

    def remove(self) -> None:
        """Unregister the underlying sprite from the GameBoy render list."""
        self._gb.remove_sprite(self.sprite)

    def __repr__(self) -> str:
        return (
            f"SpriteGroup(anim={self._current!r}, "
            f"frame={self._frame_idx}, x={self.x}, y={self.y})"
        )
