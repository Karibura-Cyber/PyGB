"""TMX demo — load topWorld.tmx with full-colour rendering and a movable player.

Requires:
    pip install pytmx
"""

import sys
import os
sys.path.insert(0, "..")

import json
import pygame
from pygb import GameBoy, Tile, Camera, CollisionMap, load_tmx
import pygb.color as color

TMX_PATH  = os.path.join(os.path.dirname(__file__), "assets", "tilemaps", "topWorld.tmx")
COLL_PATH = os.path.join(os.path.dirname(__file__), "assets", "tilemaps", "topWorld_collision.json")

gb = GameBoy(title="TMX Demo", scale=3)

player  = None
cam     = None
result  = None
cmap    = None
px, py  = 0.0, 0.0

PLAYER_TILE = Tile([
    [0,0,1,1,1,1,0,0],
    [0,1,3,3,3,3,1,0],
    [0,1,3,2,2,3,1,0],
    [0,1,3,3,3,3,1,0],
    [0,0,1,1,1,1,0,0],
    [0,0,1,0,0,1,0,0],
    [0,0,1,0,0,1,0,0],
    [0,0,0,0,0,0,0,0],
])

def render_layer(tilemap, surfaces, ts, scroll_x, scroll_y, target):
    """Blit one TMX tile layer at full colour, respecting scroll."""
    cols = gb.width  // ts + 2
    rows = gb.height // ts + 2
    for ty in range(rows):
        for tx in range(cols):
            map_tx = (tx + scroll_x // ts) % tilemap.WIDTH
            map_ty = (ty + scroll_y // ts) % tilemap.HEIGHT
            idx = tilemap.get(map_tx, map_ty)
            if idx in surfaces:
                sx = tx * ts - (scroll_x % ts)
                sy = ty * ts - (scroll_y % ts)
                target.blit(surfaces[idx], (sx, sy))

@gb.on_start
def init():
    global player, cam, cmap, px, py, result

    result = load_tmx(gb, TMX_PATH, bg_layer=0)

    # Disable the built-in BG renderer — we draw all layers manually in on_draw
    gb.graphics.bg_enabled = False

    # Load collision map from JSON saved by the editor
    ts = result.tile_size
    cmap = CollisionMap(result.map_cols, result.map_rows, tile_size=ts)
    if os.path.exists(COLL_PATH):
        with open(COLL_PATH) as f:
            saved = json.load(f)
        cmap.from_grid(saved["data"], solid_value=1)
        print(f"Collision loaded: {COLL_PATH}")
    else:
        print(f"No collision file found at {COLL_PATH!r} — player moves freely.")

    px = float(result.world_w // 2)
    py = float(result.world_h // 2)

    player = gb.create_sprite(PLAYER_TILE, x=int(px), y=int(py))

    cam = Camera(gb.graphics,
                 world_w=result.world_w,
                 world_h=result.world_h,
                 screen_w=gb.width,
                 screen_h=gb.height)
    cam.follow(px, py, smooth=1.0)

    print(f"Map: {result.map_cols}×{result.map_rows} tiles  "
          f"({result.world_w}×{result.world_h} px)  "
          f"tile_size={result.tile_size}")
    print(f"Layers: {result.layer_order}")
    print(f"VRAM tiles loaded: {gb.graphics.tile_count}")

@gb.on_update
def update():
    global px, py

    if player is None:
        return

    dx, dy = gb.input.direction()
    speed  = 2

    px, py = cmap.resolve(px, py, 8, 8, dx * speed, dy * speed)
    px = max(0, min(result.world_w - 8, px))
    py = max(0, min(result.world_h - 8, py))

    if dx < 0:
        player.flip_x = True
    elif dx > 0:
        player.flip_x = False

    cam.follow(px, py, smooth=0.15)
    player.x = int(px) - gb.graphics.scroll_x
    player.y = int(py) - gb.graphics.scroll_y

    if gb.input.pressed("start"):
        gb.quit()

@gb.on_draw
def draw():
    if result is None:
        return

    surf   = gb.surface
    ts     = result.tile_size
    sx     = gb.graphics.scroll_x
    sy     = gb.graphics.scroll_y
    surfs  = result.surfaces

    # Clear background to black
    surf.fill((0, 0, 0))

    # Draw all tile layers in order (bottom to top)
    for name in result.layer_order:
        render_layer(result.layers[name], surfs, ts, sx, sy, surf)

    # Draw player on top
    if player is not None:
        tile_surf = pygame.Surface((8, 8), pygame.SRCALPHA)
        pal = [(224,248,208),(136,192,112),(52,104,86),(8,24,32)]
        for row in range(8):
            for col in range(8):
                ci = PLAYER_TILE.get_pixel(col, row)
                if ci != 0:
                    tile_surf.set_at((col, row), pal[ci])
        surf.blit(tile_surf, (player.x, player.y))

gb.run()
