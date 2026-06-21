"""Mini platformer — gravity, jumping, floor/platform collision, animation."""

import sys
sys.path.insert(0, "..")

from pygb import GameBoy, Tile, Button, Animation, Timer, build_font_tiles, draw_text
import pygb.color as color

gb = GameBoy(title="Mini Platformer", scale=3, palette=color.GBC)

# ── tile definitions ────────────────────────────────────────────────────────────

sky_tile   = Tile.solid(0)
grass_tile = Tile([
    [3,3,3,3,3,3,3,3],
    [2,3,2,3,3,2,3,2],
    [2,2,2,2,2,2,2,2],
    [1,1,2,1,1,2,1,1],
    [1,1,1,1,1,1,1,1],
    [1,1,1,1,1,1,1,1],
    [1,1,1,1,1,1,1,1],
    [1,1,1,1,1,1,1,1],
])
brick_tile = Tile([
    [3,3,3,3,2,3,3,3],
    [3,1,1,1,2,1,1,3],
    [3,1,1,1,2,1,1,3],
    [2,2,2,2,2,2,2,2],
    [3,1,1,2,1,1,1,3],
    [3,1,1,2,1,1,1,3],
    [3,1,1,2,1,1,1,3],
    [2,2,2,2,2,2,2,2],
])

# Player frames — idle and walk (2-frame cycle)
player_idle = Tile([
    [0,0,1,1,1,1,0,0],
    [0,0,1,3,3,1,0,0],
    [0,0,1,3,3,1,0,0],
    [0,0,1,1,1,1,0,0],
    [0,1,1,1,1,1,1,0],
    [0,0,1,0,0,1,0,0],
    [0,0,1,0,0,1,0,0],
    [0,0,0,0,0,0,0,0],
])
player_walk1 = Tile([
    [0,0,1,1,1,1,0,0],
    [0,0,1,3,3,1,0,0],
    [0,0,1,3,3,1,0,0],
    [0,0,1,1,1,1,0,0],
    [0,1,1,1,1,1,1,0],
    [0,1,1,0,0,0,0,0],
    [0,0,0,0,0,1,1,0],
    [0,0,0,0,0,0,0,0],
])
player_jump = Tile([
    [0,0,1,1,1,1,0,0],
    [0,0,1,3,3,1,0,0],
    [0,0,1,3,3,1,0,0],
    [0,0,1,1,1,1,0,0],
    [0,1,1,1,1,1,1,0],
    [1,0,1,0,0,1,0,1],
    [0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0],
])

# Register tiles
sky_idx    = gb.graphics.add_tile(sky_tile)
grass_idx  = gb.graphics.add_tile(grass_tile)
brick_idx  = gb.graphics.add_tile(brick_tile)
idle_idx   = gb.graphics.add_tile(player_idle)
walk1_idx  = gb.graphics.add_tile(player_walk1)
jump_idx   = gb.graphics.add_tile(player_jump)

# Font for HUD
font_tiles, char_map = build_font_tiles()
font_start = gb.graphics.add_tiles(font_tiles)

# Enable window layer for HUD
gb.graphics.window_enabled = True
gb.graphics.window_y = 136  # just the bottom strip

# Player sprite starts at player_idle
player = gb.create_sprite(player_idle, x=76, y=100)

# ── level layout ─────────────────────────────────────────────────────────────

# Floor row = tile row 15 (y=120), platforms at rows 12 and 10
FLOOR_Y    = 128   # pixel y of the floor surface
PLATFORMS  = [
    (3, 10, 14, 12),   # (tile x, tile y, width in tiles, pixel y)
    (12, 8, 5, 10),
]

def build_level():
    gb.graphics.bg.fill(sky_idx)
    # Floor
    for tx in range(32):
        gb.graphics.bg.set(tx, 15, grass_idx)
        gb.graphics.bg.set(tx, 16, brick_idx)
        gb.graphics.bg.set(tx, 17, brick_idx)
    # Platforms
    for px, py, pw, _ in PLATFORMS:
        for dx in range(pw):
            gb.graphics.bg.set(px + dx, py, grass_idx)
            gb.graphics.bg.set(px + dx, py + 1, brick_idx)

    # HUD
    draw_text(gb.graphics.window, "COINS:0", tx=0, ty=0, char_map=char_map, base_index=font_start)

# ── game state ────────────────────────────────────────────────────────────────

px_f    = 76.0
py_f    = float(FLOOR_Y - 8)
vel_y   = 0.0
GRAVITY = 0.3
JUMP_V  = -5.0
SPEED   = 2
on_ground = True
facing_right = True
walk_timer   = Timer(10)
coins        = 0

def platform_floor_at(px: float, py: float) -> float | None:
    """Return the floor y if the player (8x8) overlaps a platform, else None."""
    cx = px + 4
    foot = py + 8
    for platx, platy, platw, plat_pxy in PLATFORMS:
        left  = platx * 8
        right = (platx + platw) * 8
        if left <= cx <= right and plat_pxy - 4 <= foot <= plat_pxy + 4:
            return float(plat_pxy)
    return None

@gb.on_start
def init():
    build_level()

@gb.on_update
def update():
    global px_f, py_f, vel_y, on_ground, facing_right, coins

    dx, _ = gb.input.direction()

    # Horizontal movement
    px_f += dx * SPEED
    px_f = max(0, min(152, px_f))
    if dx > 0:
        facing_right = True
    elif dx < 0:
        facing_right = False

    # Jump
    if on_ground and gb.input.pressed(Button.A):
        vel_y = JUMP_V
        on_ground = False
        gb.audio.ch1.tone(523, 60)   # C5

    # Gravity
    vel_y += GRAVITY
    py_f  += vel_y

    # Floor collision
    if py_f + 8 >= FLOOR_Y:
        py_f    = float(FLOOR_Y - 8)
        vel_y   = 0.0
        on_ground = True
    else:
        # Platform collision
        floor = platform_floor_at(px_f, py_f)
        if floor is not None and vel_y >= 0:
            py_f    = floor - 8
            vel_y   = 0.0
            on_ground = True
        else:
            on_ground = False

    # Choose sprite tile
    if not on_ground:
        frame_tile = player_jump
    elif dx != 0:
        ticked = walk_timer.tick()
        frame_tile = player_walk1 if (gb.frame // 10) % 2 == 0 else player_idle
    else:
        frame_tile = player_idle

    player.tile    = frame_tile
    player.x       = int(px_f)
    player.y       = int(py_f)
    player.flip_x  = not facing_right

    # Camera follow (horizontal)
    cam_x = int(px_f) - 76
    gb.graphics.scroll_to(max(0, cam_x), 0)

    # Update HUD
    draw_text(gb.graphics.window, f"COINS:{coins}  ", tx=0, ty=0, char_map=char_map, base_index=font_start)

gb.run()
