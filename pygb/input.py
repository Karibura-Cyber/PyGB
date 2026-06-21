"""Joypad input manager.

Maps keyboard keys → Game Boy buttons with held / just-pressed / just-released
state tracking per frame.
"""

from __future__ import annotations
from typing import Set


class Button:
    """Game Boy button name constants."""
    A      = "a"
    B      = "b"
    START  = "start"
    SELECT = "select"
    UP     = "up"
    DOWN   = "down"
    LEFT   = "left"
    RIGHT  = "right"

    ALL = (A, B, START, SELECT, UP, DOWN, LEFT, RIGHT)


class Input:
    """Per-frame joypad state.

    Key bindings (default):
        Z / J    → A
        X / K    → B
        Enter    → Start
        RShift   → Select
        Arrow keys → D-pad
    """

    def __init__(self) -> None:
        """Initialize empty held/pressed/released state for all buttons."""
        self._held:     Set[str] = set()
        self._pressed:  Set[str] = set()  # just pressed this frame
        self._released: Set[str] = set()  # just released this frame

        # Populated on first pygame import
        self._key_map: dict = {}

    def _build_key_map(self) -> None:
        """Build the pygame key-code → button name mapping (called lazily)."""
        import pygame
        self._key_map = {
            pygame.K_z:       Button.A,
            pygame.K_j:       Button.A,
            pygame.K_x:       Button.B,
            pygame.K_k:       Button.B,
            pygame.K_RETURN:  Button.START,
            pygame.K_RSHIFT:  Button.SELECT,
            pygame.K_LSHIFT:  Button.SELECT,
            pygame.K_UP:      Button.UP,
            pygame.K_DOWN:    Button.DOWN,
            pygame.K_LEFT:    Button.LEFT,
            pygame.K_RIGHT:   Button.RIGHT,
            pygame.K_w:       Button.UP,
            pygame.K_s:       Button.DOWN,
            pygame.K_a:       Button.LEFT,
            pygame.K_d:       Button.RIGHT,
        }

    def update(self, events: list) -> None:
        """Call once per frame with the pygame event list."""
        import pygame
        if not self._key_map:
            self._build_key_map()

        self._pressed.clear()
        self._released.clear()

        for event in events:
            if event.type == pygame.KEYDOWN:
                btn = self._key_map.get(event.key)
                if btn:
                    self._held.add(btn)
                    self._pressed.add(btn)
            elif event.type == pygame.KEYUP:
                btn = self._key_map.get(event.key)
                if btn:
                    self._held.discard(btn)
                    self._released.add(btn)

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def held(self, button: str) -> bool:
        """True while button is held down."""
        return button in self._held

    def pressed(self, button: str) -> bool:
        """True only on the frame the button was first pressed."""
        return button in self._pressed

    def released(self, button: str) -> bool:
        """True only on the frame the button was released."""
        return button in self._released

    # Convenient aliases
    is_down       = held
    just_pressed  = pressed
    just_released = released

    def any_held(self) -> bool:
        """Return True if at least one button is currently held down."""
        return bool(self._held)

    def any_pressed(self) -> bool:
        """Return True if at least one button was first pressed this frame."""
        return bool(self._pressed)

    def direction(self) -> tuple[int, int]:
        """Return (dx, dy) from D-pad: values in {-1, 0, 1}."""
        dx = (1 if self.held(Button.RIGHT) else 0) - (1 if self.held(Button.LEFT) else 0)
        dy = (1 if self.held(Button.DOWN)  else 0) - (1 if self.held(Button.UP)   else 0)
        return dx, dy

    def __repr__(self) -> str:
        return f"Input(held={sorted(self._held)})"
