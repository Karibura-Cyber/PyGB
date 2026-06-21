"""PyGB + Tiled TMX demo — full-colour dungeon map with player and collision.

Controls:
    Arrow keys   move
    Escape       quit

Requires:
    pip install pygame-ce pytmx
"""

import os
import sys
import json
sys.path.insert(0, "..")

import pygame
from pygb import GameBoy, Tile, Camera, CollisionMap, load_tmx, clamp

# ── Paths ─────────────────────────────────────────────────────────────────────

DIR       = os.path.dirname(__file__)
TMX_PATH  = os.path.join(DIR, "assets", "tilemaps", "topWorld.tmx")
COLL_PATH = os.path.join(DIR, "assets", "tilemaps", "topWorld_collision.json")

# ── Engine ────────────────────────────────────────────────────────────────────

gb = GameBoy(title="PyGB TMX Demo", scale=3)

# ── Player ────────────────────────────────────────────────────────────────────

PLAYER_TILE = Tile([
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 3, 3, 3, 3, 1, 0],
    [0, 1, 3, 2, 2, 3, 1, 0],
    [0, 1, 3, 3, 3, 3, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 0, 1, 0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
])
PLAYER_PAL = [(224, 248, 208), (136, 192, 112), (52, 104, 86), (8, 24, 32)]
PW, PH     = 8, 8   # player hitbox size in pixels
SPEED      = 2      # pixels per frame

# ── State (filled in on_start) ────────────────────────────────────────────────

result      = None
cmap        = None
player      = None
cam         = None
player_surf = None  # pre-built once; reused every frame
px          = 0.0
py          = 0.0

# ── Helpers ───────────────────────────────────────────────────────────────────

def build_player_surface(tile: Tile, pal: list) -> pygame.Surface:
    """Convert a Tile + palette into a pygame.Surface (index 0 = transparent)."""
    surf = pygame.Surface((tile.size, tile.size), pygame.SRCALPHA)
    for row in range(tile.size):
        for col in range(tile.size):
            ci = tile.get_pixel(col, row)
            if ci != 0:
                surf.set_at((col, row), pal[ci])
    return surf


def render_layer(tilemap, surfaces, ts, scroll_x, scroll_y, target, w, h):
    """Blit one TMX tile layer at full colour with scroll offset applied."""
    cols = w // ts + 2
    rows = h // ts + 2
    ox   = scroll_x % ts
    oy   = scroll_y % ts
    for ty in range(rows):
        for tx in range(cols):
            map_tx = (tx + scroll_x // ts) % tilemap.WIDTH
            map_ty = (ty + scroll_y // ts) % tilemap.HEIGHT
            idx    = tilemap.get(map_tx, map_ty)
            if idx in surfaces:
                target.blit(surfaces[idx], (tx * ts - ox, ty * ts - oy))


# ── Lifecycle ─────────────────────────────────────────────────────────────────

@gb.on_start
def init():
    global result, cmap, player, cam, player_surf, px, py

    # Load TMX map — sets gb.tile_size, gb.graphics.bg automatically
    result = load_tmx(gb, TMX_PATH, bg_layer=0)
    gb.graphics.bg_enabled = False  # use on_draw for full-colour rendering

    # Collision map from editor JSON
    ts   = result.tile_size
    cmap = CollisionMap(result.map_cols, result.map_rows, tile_size=ts)
    if os.path.exists(COLL_PATH):
        with open(COLL_PATH) as f:
            saved = json.load(f)
        cmap.from_grid(saved["data"], solid_value=1)
        print(f"Collision loaded ({saved['cols']}×{saved['rows']} tiles)")
    else:
        print("No collision file — player moves freely.")

    # Spawn player at map centre
    px, py      = float(result.world_w // 2), float(result.world_h // 2)
    player      = gb.create_sprite(PLAYER_TILE, x=int(px), y=int(py))
    player_surf = build_player_surface(PLAYER_TILE, PLAYER_PAL)

    # Camera
    cam = Camera(
        gb.graphics,
        world_w=result.world_w, world_h=result.world_h,
        screen_w=gb.width,      screen_h=gb.height,
    )
    cam.follow(px, py, smooth=1.0)

    print(f"Map: {result.map_cols}×{result.map_rows} tiles  "
          f"world: {result.world_w}×{result.world_h} px  "
          f"tile: {result.tile_size}px")
    print(f"Layers: {result.layer_order}")
    print(f"VRAM: {gb.graphics.tile_count} tiles")


@gb.on_update
def update():
    global px, py

    dx, dy = gb.input.direction()

    # Move with collision sliding
    px, py = cmap.resolve(px, py, PW, PH, dx * SPEED, dy * SPEED)
    px = clamp(px, 0, result.world_w - PW)
    py = clamp(py, 0, result.world_h - PH)

    # Flip sprite to face movement direction
    if dx < 0:
        player.flip_x = True
    elif dx > 0:
        player.flip_x = False

    # Camera follow with smooth lerp
    cam.follow(px, py, smooth=0.15)

    # Keep sprite aligned to world position minus camera scroll
    player.x = int(px) - gb.graphics.scroll_x
    player.y = int(py) - gb.graphics.scroll_y

    if gb.input.pressed("start"):
        gb.quit()


@gb.on_draw
def draw():
    surf  = gb.surface
    sx    = gb.graphics.scroll_x
    sy    = gb.graphics.scroll_y
    ts    = result.tile_size
    surfs = result.surfaces

    surf.fill((0, 0, 0))

    # Draw all tile layers in TMX order (bottom → top)
    for name in result.layer_order:
        render_layer(result.layers[name], surfs, ts, sx, sy, surf,
                     gb.width, gb.height)

    # Draw player on top of tiles
    surf.blit(player_surf, (player.x, player.y))


gb.run()
