# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Table of Contents

1. [Setup](#setup)
2. [Running Examples](#running-examples)
3. [Tools](#tools)
4. [Architecture](#architecture)
   - [Render Pipeline](#render-pipeline)
   - [Subsystems](#subsystems)
   - [Key Constraints](#key-constraints)
   - [Lifecycle Hooks](#lifecycle-hooks)
5. [Tile Size](#tile-size)
6. [Tiled TMX Maps](#tiled-tmx-maps)
   - [Full-Colour Rendering](#full-colour-rendering)
   - [Collision from Editor JSON](#collision-from-editor-json-recommended)
   - [Layer-Based Collision](#layer-based-collision)
7. [Collision Editor](#collision-editor)
   - [PNG Usage](#png-usage)
   - [TMX Usage](#tmx-usage)
   - [Loading the Output](#loading-the-output)

---

## Setup

```bash
pip install pygame-ce
pip install -e .

# Optional: Pillow for loading PNG tilesets
pip install Pillow

# Optional: pytmx for loading Tiled .tmx maps
pip install pytmx
```

---

## Running Examples

```bash
python examples/hello_world.py
python examples/bouncing_ball.py
python examples/platformer.py
python examples/test_bg.py
python examples/tmx_demo.py        # requires pytmx + examples/assets/
```

---

## Tools

### Collision map editor

Paint solid/passable tiles on a PNG tileset or a Tiled `.tmx` map and save as JSON:

```bash
# PNG tileset
python -m pygb.editor <image.png>
python -m pygb.editor <image.png> output.json

# Tiled TMX map (all tile layers rendered automatically)
python -m pygb.editor <map.tmx>
python -m pygb.editor <map.tmx> output.json
```

---

## Architecture

PyGB is a library, not an application. The entry point for every game is `GameBoy` (`pygb/game.py`), which owns all subsystems and runs the pygame event/render loop.

### Render Pipeline

Executed each frame in `GameBoy._render`:

1. Clear surface to `palette[bg_palette[0]]`
2. BG tilemap (`graphics.bg`) — scrollable with `scroll_x/y`
3. Priority sprites (drawn behind BG colors 1–3)
4. Normal sprites (on top of BG)
5. Window tilemap (`graphics.window`) — fixed overlay (HUD)
6. `on_draw` callback — raw pygame drawing into `gb.surface`

Tile surfaces are cached in `_tile_cache` keyed by `(id(tile), palette_tuple, flip_x, flip_y, transparent_color)`. Call `gb.clear_tile_cache()` after modifying tile pixel data or swapping the palette at runtime.

### Subsystems

| Module | Class | Purpose |
|--------|-------|---------|
| `game.py` | `GameBoy` | Main loop, sprite list, screen helpers, tile cache |
| `graphics.py` | `Graphics` | VRAM tile list (max 256), BG/Window `TileMap`s, palettes, scroll |
| `tilemap.py` | `TileMap` | 2-D grid of tile indices, wraps at boundaries (torus) |
| `tile.py` | `Tile` | N×N pixel grid of color indices 0–3; size defaults to 8 |
| `sprite.py` | `Sprite` | Position, flip, palette slot, AABB collision |
| `spritegroup.py` | `SpriteGroup` | Sprite + named animation states, calls `gb.create_sprite` internally |
| `input.py` | `Input`, `Button` | Per-frame held/pressed/released state |
| `audio.py` | `Audio`, channels | Four GB-style channels (pulse×2, wave, noise) via pygame mixer |
| `collision.py` | `CollisionMap` | Tile-resolution solid map; `resolve()` does AABB sliding movement |
| `assets.py` | — | PNG → `Tile` conversion, luminance quantisation or explicit palette |
| `tmx.py` | `TmxResult`, `TmxObject` | Tiled `.tmx` loader via `pytmx`; `load_tmx(gb, path)` populates VRAM and `graphics.bg` |
| `font.py` | — | Built-in 8×8 bitmap font; `build_font_tiles` / `draw_text` |
| `utils.py` | `Timer`, `Rect`, `Camera`, `Animation`, `RNG` | Helpers |
| `color.py` | — | Named palettes: `DMG`, `GRAY`, `POCKET`, `GBC` |
| `constants.py` | — | Legacy hardware constants; `TILE_SIZE = 8` kept for reference |

### Key Constraints

- **VRAM**: 256 tiles max (`graphics.add_tile` raises `RuntimeError` when full)
- **Sprites**: 40 max (no engine enforcement, just a design target)
- **Color indices**: 0–3 (index 0 is transparent for sprites)
- **Default viewport**: 160×144 pixels; configurable via `GameBoy(width=..., height=...)`
- **CollisionMap cells**: one cell per tile; `resolve()` tunnels if displacement ≥ `tile_size` px/frame
- **Player vs tile size**: the player hitbox (`w`, `h`) passed to `resolve()` can be smaller than `tile_size` — e.g. an 8×8 sprite on a 16×16 tile map works correctly

### Lifecycle Hooks

```python
@gb.on_start   # once, before loop
@gb.on_update  # every frame — game logic goes here
@gb.on_draw    # every frame — after automatic render, for raw pygame drawing
@gb.on_stop    # once, on exit
```

---

## Tile Size

PyGB defaults to 8×8 px tiles (classic Game Boy). Pass `tile_size=N` to use a different size — required when loading Tiled maps with 16×16 or other tile sizes.

```python
gb = GameBoy(title="My Game", tile_size=16)
```

`Tile` infers its size from the pixel data passed in — no extra argument needed:

```python
my_tile = Tile([[...16 rows of 16 values...]])  # size auto-detected as 16
```

`CollisionMap` also needs the matching tile size:

```python
cmap = CollisionMap(map_cols, map_rows, tile_size=16)
```

`load_tmx` sets `gb.tile_size` automatically so you rarely need to set it manually.

---

## Tiled TMX Maps

```bash
pip install pytmx
```

```python
from pygb import GameBoy, load_tmx, CollisionMap, Camera
import pygb.color as color

gb = GameBoy(title="Tiled Demo", scale=3)

@gb.on_start
def init():
    result = load_tmx(gb, "level1.tmx")
    # gb.tile_size is set automatically from the TMX file
```

`TmxResult` fields:

| Field | Type | Description |
|-------|------|-------------|
| `tile_size` | `int` | Tile width/height in pixels |
| `map_cols` | `int` | Map width in tiles |
| `map_rows` | `int` | Map height in tiles |
| `world_w` | `int` | World width in pixels |
| `world_h` | `int` | World height in pixels |
| `layers` | `dict[str, TileMap]` | All tile layers keyed by name |
| `layer_order` | `list[str]` | Layer names in TMX order (bottom → top) |
| `objects` | `dict[str, list[TmxObject]]` | Object groups keyed by name |
| `properties` | `dict` | Map-level custom properties |
| `surfaces` | `dict[int, Surface]` | Raw pygame surfaces keyed by VRAM index for full-colour rendering |

The 256-tile VRAM limit still applies — maps with more than 256 unique tiles raise `RuntimeError`.

### Full-Colour Rendering

The standard PyGB render pipeline quantises tiles to 4 colors. For TMX maps with rich tilesets, use `result.surfaces` to render at full colour via `on_draw`:

```python
@gb.on_start
def init():
    result = load_tmx(gb, "level1.tmx")
    gb.graphics.bg_enabled = False   # disable 4-colour pipeline

@gb.on_draw
def draw():
    ts = result.tile_size
    sx = gb.graphics.scroll_x
    sy = gb.graphics.scroll_y
    gb.surface.fill((0, 0, 0))

    for name in result.layer_order:           # draw layers bottom → top
        tilemap = result.layers[name]
        cols = gb.width  // ts + 2
        rows = gb.height // ts + 2
        for ty in range(rows):
            for tx in range(cols):
                map_tx = (tx + sx // ts) % tilemap.WIDTH
                map_ty = (ty + sy // ts) % tilemap.HEIGHT
                idx = tilemap.get(map_tx, map_ty)
                if idx in result.surfaces:
                    gb.surface.blit(result.surfaces[idx],
                                    (tx * ts - sx % ts, ty * ts - sy % ts))
```

### Collision from Editor JSON (recommended)

Paint solid tiles in the editor, save the JSON, then load it at runtime:

```python
import json
from pygb import CollisionMap

with open("topWorld_collision.json") as f:
    saved = json.load(f)

cmap = CollisionMap(saved["cols"], saved["rows"], tile_size=result.tile_size)
cmap.from_grid(saved["data"], solid_value=1)

# In on_update — player stops flush against walls, slides along them:
px, py = cmap.resolve(px, py, player_w, player_h, dx * speed, dy * speed)
px = max(0, min(result.world_w - player_w, px))
py = max(0, min(result.world_h - player_h, py))
```

If the JSON file is missing the player moves freely (useful during early development):

```python
cmap = CollisionMap(result.map_cols, result.map_rows, tile_size=result.tile_size)
if os.path.exists(COLL_PATH):
    with open(COLL_PATH) as f:
        saved = json.load(f)
    cmap.from_grid(saved["data"], solid_value=1)
```

### Layer-Based Collision

Alternatively build from a dedicated TMX wall layer — no editor needed:

```python
cmap = CollisionMap(result.map_cols, result.map_rows, tile_size=result.tile_size)
wall_layer = result.layers.get("wall")
if wall_layer:
    for ty in range(result.map_rows):
        for tx in range(result.map_cols):
            if wall_layer.get(tx, ty) > 0:
                cmap.set(tx, ty, solid=True)
```

Or from specific tile indices:

```python
cmap.from_tilemap(result.layers["ground"], solid_indices={wall_idx, fence_idx})
```

---

## Collision Editor

### PNG Usage

```bash
python -m pygb.editor examples/ground.png
python -m pygb.editor examples/ground.png examples/ground_collision.json
```

### TMX Usage

Pass a `.tmx` file directly — the editor renders all tile layers into one image and uses the TMX tile size for the grid automatically:

```bash
python -m pygb.editor examples/assets/tilemaps/topWorld.tmx
python -m pygb.editor examples/assets/tilemaps/topWorld.tmx my_collision.json
```

Editor controls:

| Input | Action |
|-------|--------|
| Left click / drag | Mark tiles solid (red) |
| Right click / drag | Mark tiles passable |
| Middle drag | Pan |
| Scroll up/down | Zoom in / out |
| `S` | Save |
| `R` | Clear all solid tiles |
| `Z` | Undo last stroke |
| `Escape` | Quit |

### Loading the Output

JSON format: `{ "cols": N, "rows": N, "data": [[0/1, ...], ...] }`

```python
from pygb import CollisionMap
import json

with open("topWorld_collision.json") as f:
    saved = json.load(f)

cmap = CollisionMap(saved["cols"], saved["rows"], tile_size=result.tile_size)
cmap.from_grid(saved["data"], solid_value=1)

# In on_update — player hitbox can be smaller than tile_size:
px, py = cmap.resolve(px, py, 8, 8, dx * speed, dy * speed)
px = max(0, min(world_w - 8, px))
py = max(0, min(world_h - 8, py))
```
