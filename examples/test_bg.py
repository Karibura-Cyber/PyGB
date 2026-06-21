"""Test: tiled PNG background with a player, camera follow, and collision.

Requires examples/ground.png — an image whose dimensions are multiples of 8.
If no ground_collision.json exists the player moves freely through everything.
"""

import sys
import os
sys.path.insert(0, "..")

from pygb import GameBoy, Tile, Camera, TileMap, CollisionMap, load_tileset
import pygb.color as color

IMG_PATH = os.path.join(os.path.dirname(__file__), "ground.png")

gb = GameBoy(title="PNG Background + Collision", scale=3, palette=color.DMG)

player = None
cam    = None
coll   = None
px, py = 80, 72   # start near centre of 160×144 world (will be overridden)

WORLD_W = 0
WORLD_H = 0

COLL_FILE = os.path.join(os.path.dirname(__file__), "ground_collision.json")

@gb.on_start
def init():
    global player, cam, coll, px, py, WORLD_W, WORLD_H

    # --- Load tileset from PNG ---
    if not os.path.exists(IMG_PATH):
        print(f"ERROR: '{IMG_PATH}' not found.")
        print("Place a ground.png image (dimensions must be multiples of 8) in the examples/ folder.")
        gb.quit()
        return

    import pygame
    img = pygame.image.load(IMG_PATH)
    img_w, img_h = img.get_size()
    MAP_COLS = img_w // 8
    MAP_ROWS = img_h // 8
    WORLD_W  = img_w
    WORLD_H  = img_h

    gb.graphics.bg = TileMap(width=MAP_COLS, height=MAP_ROWS)

    tiles = load_tileset(IMG_PATH)
    seen, layout = {}, []
    for ty in range(MAP_ROWS):
        for tx in range(MAP_COLS):
            tile = tiles[ty * MAP_COLS + tx]
            key  = tuple(tile._data[r][c] for r in range(8) for c in range(8))
            if key not in seen:
                seen[key] = gb.graphics.add_tile(tile)
            layout.append(seen[key])
    for i, idx in enumerate(layout):
        gb.graphics.bg.set(i % MAP_COLS, i // MAP_COLS, idx)

    # --- Collision map ---
    coll = CollisionMap(MAP_COLS, MAP_ROWS)
    if os.path.exists(COLL_FILE):
        import json
        with open(COLL_FILE) as f:
            data = json.load(f)
        grid = data["data"]
        for ty, row in enumerate(grid):
            for tx, val in enumerate(row):
                if val:
                    coll.set(tx, ty, True)
    else:
        print("No collision file — player moves freely.")

    # --- Player sprite ---
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
    px, py = WORLD_W // 2, WORLD_H // 2
    player = gb.create_sprite(player_tile, x=px - gb.graphics.scroll_x,
                                           y=py - gb.graphics.scroll_y)

    cam = Camera(gb.graphics, world_w=WORLD_W, world_h=WORLD_H,
                 screen_w=gb.width, screen_h=gb.height)
    cam.follow(px, py, smooth=1.0)

@gb.on_update
def update():
    global px, py

    if player is None:
        return

    dx, dy = gb.input.direction()
    speed  = 2

    if dx != 0:
        nx = max(0, min(WORLD_W - 8, px + dx * speed))
        if coll is None or not coll.overlaps_rect(nx, py, 8, 8):
            px = nx
        player.flip_x = dx < 0

    if dy != 0:
        ny = max(0, min(WORLD_H - 8, py + dy * speed))
        if coll is None or not coll.overlaps_rect(px, ny, 8, 8):
            py = ny

    cam.follow(px, py, smooth=0.25)
    player.x = px - gb.graphics.scroll_x
    player.y = py - gb.graphics.scroll_y

    if gb.input.pressed("start"):
        gb.quit()

gb.run()
