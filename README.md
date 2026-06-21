# PyGB

A **Game Boy-style 2D game making library** for Python, built on [pygame-ce](https://pyga.me).

160×144 viewport · 4-colour palette · GB-authentic audio channels · Tiled TMX map support · Collision editor

---

## Install

```bash
pip install pygb
```

**Optional extras:**

```bash
pip install "pygb[tmx]"    # Tiled .tmx map support (pytmx)
pip install "pygb[image]"  # PNG tileset loading   (Pillow)
pip install "pygb[all]"    # Both of the above
```

---

## Quick Start

```python
from pygb import GameBoy, Tile
import pygb.color as color

gb = GameBoy(title="My Game", scale=3, palette=color.DMG)

player_tile = Tile([
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 3, 3, 3, 3, 1, 0],
    [0, 1, 3, 2, 2, 3, 1, 0],
    [0, 1, 3, 3, 3, 3, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 0, 1, 0, 0, 1, 0, 0],
    [0, 0, 1, 0, 0, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
])
player = gb.create_sprite(player_tile, x=76, y=68)

@gb.on_update
def update():
    dx, dy = gb.input.direction()
    player.move(dx * 2, dy * 2)
    player.clamp(0, 0, 152, 136)
    if dx < 0:  player.flip_x = True
    elif dx > 0: player.flip_x = False

gb.run()
```

---

## TMX Map Example

Load a full-colour Tiled map with camera and tile collision:

```python
import os, json
from pygb import GameBoy, Tile, Camera, CollisionMap, load_tmx, clamp

gb = GameBoy(title="TMX Demo", scale=3)

@gb.on_start
def init():
    global result, cmap, player, cam, px, py

    result = load_tmx(gb, "level.tmx")
    gb.graphics.bg_enabled = False  # full-colour rendering via on_draw

    cmap = CollisionMap(result.map_cols, result.map_rows, tile_size=result.tile_size)
    if os.path.exists("level_collision.json"):
        with open("level_collision.json") as f:
            saved = json.load(f)
        cmap.from_grid(saved["data"], solid_value=1)

    px, py = float(result.world_w // 2), float(result.world_h // 2)
    cam = Camera(gb.graphics,
                 world_w=result.world_w, world_h=result.world_h,
                 screen_w=gb.width, screen_h=gb.height)
    cam.follow(px, py, smooth=1.0)

@gb.on_update
def update():
    global px, py
    dx, dy = gb.input.direction()
    px, py = cmap.resolve(px, py, 8, 8, dx * 2, dy * 2)
    px = clamp(px, 0, result.world_w - 8)
    py = clamp(py, 0, result.world_h - 8)
    cam.follow(px, py, smooth=0.15)

@gb.on_draw
def draw():
    ts, sx, sy = result.tile_size, gb.graphics.scroll_x, gb.graphics.scroll_y
    gb.surface.fill((0, 0, 0))
    for name in result.layer_order:
        tilemap = result.layers[name]
        cols, rows = gb.width // ts + 2, gb.height // ts + 2
        for ty in range(rows):
            for tx in range(cols):
                idx = tilemap.get((tx + sx // ts) % tilemap.WIDTH,
                                  (ty + sy // ts) % tilemap.HEIGHT)
                if idx in result.surfaces:
                    gb.surface.blit(result.surfaces[idx],
                                    (tx * ts - sx % ts, ty * ts - sy % ts))

gb.run()
```

---

## Collision Editor

Paint solid/passable tiles on a PNG tileset or a Tiled `.tmx` map and save as JSON:

```bash
# PNG tileset
pygb-editor tileset.png
pygb-editor tileset.png output.json

# Tiled TMX map (all layers rendered automatically)
pygb-editor level.tmx
pygb-editor level.tmx level_collision.json

# Advanced editor with startup dialog
pygb-collision
pygb-collision tileset.png
pygb-collision --blank 20x18 blank_collision.json
```

| Key | Action |
|-----|--------|
| Left click / drag | Mark tiles solid |
| Right click / drag | Mark tiles passable |
| Middle drag | Pan |
| Scroll | Zoom in / out |
| `S` | Save JSON |
| `Z` | Undo |
| `R` | Clear all |
| `Escape` | Quit |

---

## Features

| Feature | Details |
|---------|---------|
| Viewport | 160×144 px (configurable) |
| Tile size | Any size (default 8×8, auto-detected) |
| VRAM | 256 tiles max |
| Sprites | Position, flip, palette, AABB collision |
| Tilemaps | BG (scrollable) + Window (HUD overlay) |
| Palettes | DMG · GRAY · POCKET · GBC |
| Audio | 2× Pulse · Wave · Noise (GB-style) |
| TMX loader | Full-colour rendering via pytmx |
| Collision | Tile-resolution AABB with wall sliding |
| Font | Built-in 8×8 bitmap font |
| Utilities | Camera · Timer · Animation · RNG · Rect |

---

## Lifecycle Hooks

```python
@gb.on_start    # called once before the loop
@gb.on_update   # called every frame — game logic
@gb.on_draw     # called every frame — raw pygame drawing
@gb.on_stop     # called once on exit
```

---

## Requirements

- Python ≥ 3.9
- pygame-ce ≥ 2.5
- pytmx ≥ 3.31 *(optional, for TMX loading)*
- Pillow ≥ 9.0 *(optional, for PNG tileset loading)*

---

## License

MIT — see [LICENSE](LICENSE) for details.
