"""Small utility classes — Timer, Rect, Camera, Animation, RNG."""

from __future__ import annotations
import math
from typing import Callable, Generic, List, Optional, TypeVar

T = TypeVar("T")


class Timer:
    """Count-down / repeating frame timer."""

    def __init__(self, frames: int, repeat: bool = True) -> None:
        """Create a timer that fires every *frames* frames; repeats by default."""
        self.frames  = max(1, frames)
        self.repeat  = repeat
        self._count  = 0
        self._done   = False

    def tick(self) -> bool:
        """Advance by one frame. Returns True when the timer fires."""
        if self._done and not self.repeat:
            return False
        self._count += 1
        if self._count >= self.frames:
            self._count = 0
            self._done = True
            return True
        return False

    def reset(self) -> None:
        """Restart the timer from zero."""
        self._count = 0
        self._done  = False

    @property
    def progress(self) -> float:
        """0.0 → 1.0 fraction of the current cycle."""
        return self._count / self.frames


class Rect:
    """Axis-aligned bounding rectangle for collision checks."""

    def __init__(self, x: float, y: float, w: float, h: float) -> None:
        """Create a rectangle at (x, y) with the given width and height."""
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    @property
    def right(self) -> float:
        """Right edge (x + w)."""
        return self.x + self.w

    @property
    def bottom(self) -> float:
        """Bottom edge (y + h)."""
        return self.y + self.h

    @property
    def cx(self) -> float:
        """Horizontal center of the rectangle."""
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        """Vertical center of the rectangle."""
        return self.y + self.h / 2

    def overlaps(self, other: "Rect") -> bool:
        """Return True if this rectangle intersects *other*."""
        return (
            self.x < other.right
            and self.right > other.x
            and self.y < other.bottom
            and self.bottom > other.y
        )

    def contains(self, px: float, py: float) -> bool:
        """Return True if point (px, py) is inside this rectangle."""
        return self.x <= px < self.right and self.y <= py < self.bottom

    def move(self, dx: float, dy: float) -> "Rect":
        """Return a new Rect shifted by (dx, dy) without modifying this one."""
        return Rect(self.x + dx, self.y + dy, self.w, self.h)

    def __repr__(self) -> str:
        return f"Rect({self.x}, {self.y}, {self.w}, {self.h})"


class Camera:
    """Tracks a target and updates graphics.scroll_x/y each frame."""

    def __init__(
        self,
        graphics,
        world_w: int,
        world_h: int,
        screen_w: int = None,
        screen_h: int = None,
        deadzone_x: int = 0,
        deadzone_y: int = 0,
    ) -> None:
        """Create a camera that scrolls *graphics* within a world of *world_w* × *world_h* pixels.

        Pass *screen_w*/*screen_h* to match the GameBoy viewport size when it differs from
        the default 160×144. Easiest way: ``Camera(gb.graphics, ..., screen_w=gb.width, screen_h=gb.height)``.
        """
        from .constants import SCREEN_WIDTH, SCREEN_HEIGHT
        self._gfx = graphics
        self.world_w = world_w
        self.world_h = world_h
        self.screen_w = screen_w if screen_w is not None else SCREEN_WIDTH
        self.screen_h = screen_h if screen_h is not None else SCREEN_HEIGHT
        self.deadzone_x = deadzone_x
        self.deadzone_y = deadzone_y

    def follow(self, x: float, y: float, smooth: float = 1.0) -> None:
        """Center the camera on (x, y), optionally with smoothing (0 < smooth ≤ 1)."""
        target_x = x - self.screen_w // 2
        target_y = y - self.screen_h // 2
        target_x = max(0, min(self.world_w - self.screen_w, target_x))
        target_y = max(0, min(self.world_h - self.screen_h, target_y))
        self._gfx.scroll_x += int((target_x - self._gfx.scroll_x) * smooth)
        self._gfx.scroll_y += int((target_y - self._gfx.scroll_y) * smooth)


class Animation:
    """Cycle through a list of tile indices at a set frame rate."""

    def __init__(
        self,
        frames: List[int],
        speed: int = 8,
        loop: bool = True,
    ) -> None:
        """Create an animation cycling through *frames* tile indices, advancing every *speed* game frames."""
        self.frames  = frames
        self.speed   = max(1, speed)
        self.loop    = loop
        self._tick   = 0
        self._done   = False

    def update(self) -> int:
        """Advance animation and return the current frame tile index."""
        if not self._done:
            self._tick += 1
        frame_idx = (self._tick // self.speed)
        if frame_idx >= len(self.frames):
            if self.loop:
                self._tick = 0
                frame_idx = 0
            else:
                self._done = True
                frame_idx = len(self.frames) - 1
        return self.frames[frame_idx]

    def reset(self) -> None:
        """Restart the animation from the first frame."""
        self._tick = 0
        self._done = False

    @property
    def done(self) -> bool:
        """True when a non-looping animation has played its last frame."""
        return self._done

    @property
    def current(self) -> int:
        """Return the current frame tile index without advancing the animation."""
        idx = min(self._tick // self.speed, len(self.frames) - 1)
        return self.frames[idx]


class RNG:
    """Fast LCG pseudo-random number generator (GB-style)."""

    def __init__(self, seed: int = 0x1234) -> None:
        """Seed the 16-bit LCG pseudo-random generator."""
        self._state = seed & 0xFFFF

    def next_int(self) -> int:
        """Return a pseudo-random 16-bit integer (0–65535)."""
        self._state = (self._state * 0x6C07 + 0x4651) & 0xFFFF
        return self._state

    def randint(self, lo: int, hi: int) -> int:
        """Return a pseudo-random int in [lo, hi] inclusive."""
        span = hi - lo + 1
        return lo + (self.next_int() % span)

    def choice(self, seq):
        """Return a random element from *seq*."""
        return seq[self.randint(0, len(seq) - 1)]

    def randf(self) -> float:
        """Return a pseudo-random float in [0.0, 1.0]."""
        return self.next_int() / 65535.0


def lerp(a: float, b: float, t: float) -> float:
    """Linearly interpolate from *a* to *b* by factor *t* (0.0 = a, 1.0 = b)."""
    return a + (b - a) * t


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to the range [lo, hi]."""
    return max(lo, min(hi, value))


def sign(x: float) -> int:
    """Return -1, 0, or 1 based on the sign of *x*."""
    return (x > 0) - (x < 0)
