"""PyGB — Game Boy-style game making library for Python.

Quick start::

    from pygb import GameBoy, Tile, Sprite, Button
    import pygb.color as color

    gb = GameBoy(title="My Game", scale=3)

    player_tile = Tile([
        [0,0,1,1,1,1,0,0],
        [0,1,3,3,3,3,1,0],
        [0,1,3,2,2,3,1,0],
        [0,1,3,3,3,3,1,0],
        [0,0,1,1,1,1,0,0],
        [0,0,1,0,0,1,0,0],
        [0,0,1,0,0,1,0,0],
        [0,0,0,0,0,0,0,0],
    ])

    player = gb.create_sprite(player_tile, x=76, y=68)

    @gb.on_update
    def update():
        dx, dy = gb.input.direction()
        player.move(dx, dy)
        player.clamp(0, 0, 152, 136)

    gb.run()
"""

from .game     import GameBoy
from .tile     import Tile
from .tilemap  import TileMap
from .sprite   import Sprite
from .graphics import Graphics
from .input    import Input, Button
from .audio    import Audio, PulseChannel, WaveChannel, NoiseChannel
from .utils    import Timer, Rect, Camera, Animation, RNG, lerp, clamp, sign
from .assets    import load_tileset, load_tile, tiles_from_pixels, surface_to_tile
from .collision   import CollisionMap
from .spritegroup import SpriteGroup
from .tmx         import load_tmx, TmxResult, TmxObject
from .font     import char_to_tile, build_font_tiles, draw_text
from . import color
from . import constants

__version__ = "0.1.0"
__all__ = [
    "GameBoy",
    "Tile",
    "TileMap",
    "Sprite",
    "Graphics",
    "Input",
    "Button",
    "Audio",
    "PulseChannel",
    "WaveChannel",
    "NoiseChannel",
    "Timer",
    "Rect",
    "Camera",
    "Animation",
    "RNG",
    "lerp",
    "clamp",
    "sign",
    "load_tileset",
    "load_tile",
    "tiles_from_pixels",
    "surface_to_tile",
    "CollisionMap",
    "SpriteGroup",
    "load_tmx",
    "TmxResult",
    "TmxObject",
    "char_to_tile",
    "build_font_tiles",
    "draw_text",
    "color",
    "constants",
]
