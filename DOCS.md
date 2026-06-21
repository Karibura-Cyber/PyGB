# PyGB Documentation

A Game Boy-style game engine for Python. Renders to a 160×144 pixel window using pygame-ce as the backend. All graphics use 4 color indices (0–3), 8×8 tiles, and up to 40 sprites — just like the original hardware.

---

## Installation

```bash
pip install pygame-ce
pip install -e .
```

---

## Quick Start

```python
from pygb import GameBoy, Tile, Button

gb = GameBoy(title="My Game", scale=3)

player_tile = Tile([
    [0,0,1,1,1,1,0,0],
    [0,1,3,3,3,3,1,0],
    [0,1,3,2,2,3,1,0],
    [0,0,1,1,1,1,0,0],
    [0,0,1,0,0,1,0,0],
    [0,0,1,0,0,1,0,0],
    [0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0],
])

player = gb.create_sprite(player_tile, x=76, y=68)

@gb.on_update
def update():
    dx, dy = gb.input.direction()
    player.move(dx, dy)
    player.clamp(0, 0, 152, 136)

gb.run()
```

---

## GameBoy

The main class. Owns all subsystems and runs the game loop.

```python
GameBoy(title="PyGB", scale=3, fps=60, palette=None, width=160, height=144)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `title`   | `"PyGB"` | Window title |
| `scale`   | `3`      | Integer pixel scale — physical window = `width*scale × height*scale` |
| `fps`     | `60`     | Target frames per second |
| `palette` | `color.DMG` | List of 4 RGB tuples |
| `width`   | `160`    | Internal viewport width in pixels |
| `height`  | `144`    | Internal viewport height in pixels |

```python
# Classic Game Boy (default)
gb = GameBoy(scale=3)                          # 480×432 window

# Larger viewport for bigger worlds
gb = GameBoy(width=320, height=240, scale=2)   # 640×480 window

# Tiny handheld feel
gb = GameBoy(width=80, height=72, scale=6)     # 480×432 window, half the tiles
```

### Lifecycle hooks

```python
@gb.on_start   # called once before the loop
def init(): ...

@gb.on_update  # called every frame — put all game logic here
def update(): ...

@gb.on_draw    # called after automatic rendering, for custom drawing
def draw(): ...

@gb.on_stop    # called when the window closes
def cleanup(): ...
```

### Sprite factory

```python
sprite = gb.create_sprite(tile, x=0, y=0, **kwargs)
gb.remove_sprite(sprite)
```

### Direct drawing

```python
gb.fill_screen(color)               # fill entire screen with color index 0–3
gb.draw_pixel(x, y, color)          # plot a single pixel
gb.draw_tile(tile, x, y)            # blit a tile directly (bypasses TileMap)
gb.draw_rect(x, y, w, h, color)     # filled rectangle
gb.draw_outline(x, y, w, h, color)  # 1-pixel outlined rectangle
```

### Properties

```python
gb.frame      # int — frames elapsed since run() was called
gb.surface    # pygame.Surface — raw 160×144 surface (advanced use)
gb.graphics   # Graphics subsystem
gb.input      # Input subsystem
gb.audio      # Audio subsystem
gb.sprites    # list[Sprite]
gb.palette    # list of 4 RGB tuples (can be swapped at runtime)
```

```python
gb.quit()     # signal the loop to exit after the current frame
```

---

## Tile

An 8×8 grid of color indices (0–3). Index 0 is transparent for sprites.

```python
Tile(pixels=None)   # pixels: 8×8 list of ints 0–3; all-zero if omitted
```

### Pixel access

```python
tile.get_pixel(x, y)          # → int 0–3
tile.set_pixel(x, y, color)
tile.fill(color)
```

### Transformations — return new Tile, non-destructive

```python
tile.flip_h()      # mirror horizontally
tile.flip_v()      # mirror vertically
tile.rotate_90()   # rotate 90° clockwise
tile.invert()      # map every value v → 3 - v
```

### Convenience constructors

```python
Tile.solid(color)              # all 64 pixels = color
Tile.border(outer=3, inner=0)  # 1-pixel border
Tile.checkerboard(a=0, b=3)    # alternating a/b pattern
```

### Game Boy 2bpp format

```python
data  = tile.to_2bpp()       # → 16 bytes of GB 2bpp data
tile2 = Tile.from_2bpp(data) # decode 16 bytes back into a Tile
```

---

## TileMap

A scrollable 32×32 (default) grid of tile indices. Used for the Background and Window layers. Wraps at boundaries (torus topology).

```python
TileMap(width=32, height=32)
```

### Access

```python
tilemap.set(tx, ty, index)       # write tile index
tilemap.get(tx, ty)              # read tile index
tilemap.set_tile(tx, ty, index)  # alias for set()
tilemap.get_tile(tx, ty)         # alias for get()
```

### Bulk operations

```python
tilemap.fill(index)
tilemap.fill_rect(tx, ty, w, h, index)
tilemap.clear()                              # fill with index 0
tilemap.draw_text(text, tx, ty, font_start=0)  # write ASCII using registered font tiles
```

---

## Graphics

Manages the tile VRAM registry and both background layers.

Accessed via `gb.graphics`.

### Tile VRAM

```python
idx   = gb.graphics.add_tile(tile)          # register one tile → its index
start = gb.graphics.add_tiles([t1, t2, …])  # register many → first index
gb.graphics.set_tile(index, tile)            # replace an existing tile
tile  = gb.graphics.get_tile(index)
gb.graphics.tile_count                       # int — tiles registered so far (max 256)
```

### Layers

```python
gb.graphics.bg      # TileMap — scrollable background
gb.graphics.window  # TileMap — fixed window overlay (HUD)
```

### Scroll

```python
gb.graphics.scroll_x = 0
gb.graphics.scroll_y = 0
gb.graphics.scroll(dx, dy)    # relative scroll
gb.graphics.scroll_to(x, y)  # absolute scroll
```

### Window position

```python
gb.graphics.window_x = 0
gb.graphics.window_y = 0
```

### Layer enable flags

```python
gb.graphics.bg_enabled      = True
gb.graphics.window_enabled  = False
gb.graphics.sprites_enabled = True
```

### Palettes

Each palette is a list of 4 ints mapping color index → shade index (0–3).

```python
gb.graphics.bg_palette    = [0, 1, 2, 3]    # identity (default)
gb.graphics.obj_palette0  = [0, 1, 2, 3]
gb.graphics.obj_palette1  = [0, 1, 2, 3]

gb.graphics.set_bg_palette([0, 2, 2, 3])     # remap BG colors
gb.graphics.set_obj_palette(0, [0, 1, 2, 3])
gb.graphics.set_obj_palette(1, [0, 1, 2, 3])
```

---

## Sprite

A movable 8×8 (or 8×16) object rendered on top of the background.

```python
Sprite(tile, x=0, y=0, *, tile_b=None, visible=True,
       flip_x=False, flip_y=False, palette=0, priority=False)
```

| Attribute | Description |
|-----------|-------------|
| `tile`    | Primary Tile object |
| `tile_b`  | Second tile for 8×16 mode (optional) |
| `x`, `y`  | Screen position in pixels |
| `visible` | Whether to draw this sprite |
| `flip_x`  | Mirror horizontally |
| `flip_y`  | Mirror vertically |
| `palette` | 0 or 1 — selects `obj_palette0` or `obj_palette1` |
| `priority`| If True, renders behind BG colors 1–3 |

### Movement

```python
sprite.move(dx, dy)
sprite.move_to(x, y)
sprite.clamp(x0, y0, x1, y1)   # keep inside pixel bounds
```

### Collision

```python
sprite.collides_with(other)   # → bool AABB check against another Sprite
sprite.on_screen(margin=0)    # → bool
sprite.height                 # 8 normally, 16 in 8×16 mode
```

### Flip helpers

```python
sprite.toggle_flip_x()
sprite.toggle_flip_y()
```

---

## Input

Accessed via `gb.input`. Updated automatically each frame.

### Default key bindings

| Key | Button |
|-----|--------|
| Z or J | A |
| X or K | B |
| Enter | Start |
| RShift / LShift | Select |
| Arrow keys or WASD | D-pad |
| Escape | Quit |

### Button constants

```python
from pygb import Button

Button.A, Button.B
Button.START, Button.SELECT
Button.UP, Button.DOWN, Button.LEFT, Button.RIGHT
```

### State queries

```python
gb.input.held(Button.A)      # True while held down
gb.input.pressed(Button.A)   # True on the frame it was first pressed
gb.input.released(Button.A)  # True on the frame it was released

gb.input.direction()         # → (dx, dy) from D-pad, values in {-1, 0, 1}
gb.input.any_held()          # → bool
gb.input.any_pressed()       # → bool
```

---

## Audio

Four Game Boy sound channels accessed via `gb.audio`.

| Channel | Type | Use |
|---------|------|-----|
| `gb.audio.ch1` | PulseChannel (with sweep) | Effects, lead |
| `gb.audio.ch2` | PulseChannel | Harmony |
| `gb.audio.ch3` | WaveChannel | Custom waveforms |
| `gb.audio.ch4` | NoiseChannel | Drums, explosions |

### Quick beep

```python
gb.audio.beep(freq=440, duration_ms=100, channel=0, volume=0.5)
```

### PulseChannel (ch1, ch2)

```python
gb.audio.ch1.tone(frequency, duration_ms=100, volume=None, duty=None, loops=0)
gb.audio.ch1.note("C", octave=4, duration_ms=200)   # musical note by name
gb.audio.ch1.duty = 0.5   # pulse duty cycle: 0.125, 0.25, 0.5, 0.75
```

### WaveChannel (ch3)

```python
gb.audio.ch3.play(frequency, duration_ms=200)
gb.audio.ch3.set_waveform(samples)         # list of 32 ints, each 0–15
gb.audio.ch3.wavetable = WaveChannel.SINE      # built-in waveforms
gb.audio.ch3.wavetable = WaveChannel.SAWTOOTH
gb.audio.ch3.wavetable = WaveChannel.TRIANGLE
```

### NoiseChannel (ch4)

```python
gb.audio.ch4.burst(duration_ms=100, volume=None)
```

### Per-channel control

```python
ch.volume = 0.8   # 0.0 – 1.0
ch.stop()
ch.is_busy()      # → bool
```

### Master volume & stop all

```python
gb.audio.master_volume = 0.5
gb.audio.stop_all()
```

---

## Font

Built-in 8×8 bitmap font covering printable ASCII (space through Z plus `_`).

### Build font tiles

```python
from pygb import build_font_tiles

font_tiles, char_map = build_font_tiles(
    chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 !.,",
    ink=3,    # color index for strokes (default 3 = darkest)
    paper=0,  # color index for background (default 0 = lightest)
)
font_start = gb.graphics.add_tiles(font_tiles)
```

### Draw text onto a TileMap

```python
from pygb import draw_text

draw_text(gb.graphics.bg, "HELLO WORLD", tx=1, ty=2,
          char_map=char_map, base_index=font_start)
```

### Single character tile

```python
from pygb import char_to_tile

tile = char_to_tile("A", ink=3, paper=0)
```

---

## SpriteGroup

A `Sprite` bundled with named animation states. Handles tile swapping automatically so you only call `update()` each frame.

```python
group = gb.create_group(x=40, y=64)

group.add("idle", [idle_tile],              speed=12)
group.add("walk", [walk1, walk2, walk3, walk2], speed=6)
group.add("jump", [jump_tile],              speed=1, loop=False)

group.play("idle")

@gb.on_update
def update():
    dx, _ = gb.input.direction()
    group.move(dx * 2, 0)
    group.flip_x = dx < 0

    if not group.is_playing("jump"):
        group.play("walk" if dx != 0 else "idle")

    group.update()   # advance animation and sync sprite tile
```

### Creating

```python
# Via GameBoy factory (recommended — auto-registers the sprite)
group = gb.create_group(x=0, y=0, flip_x=False, palette=0, priority=False)

# Direct construction
from pygb import SpriteGroup
group = SpriteGroup(gb, x=0, y=0)
```

### Adding animations

```python
group.add(name, tiles, speed=8, loop=True)
```

| Parameter | Description |
|-----------|-------------|
| `name`    | String key used to switch states |
| `tiles`   | List of `Tile` objects, in frame order |
| `speed`   | Frames between tile advances (lower = faster) |
| `loop`    | If `False`, stops on the last frame |

Calls can be chained: `group.add("idle", [t0]).add("walk", [t1, t2], speed=4)`

### Controlling playback

```python
group.play("walk")             # switch state (ignored if already playing)
group.play("jump", restart=True)  # force rewind even if already active
group.update()                 # call once per frame to advance frames
```

### State queries

```python
group.current        # name of the active animation, or None
group.done           # True when a non-looping animation reaches its last frame
group.frame_index    # current frame index within the active animation
group.is_playing("walk")  # → bool
```

### Sprite pass-through

All common `Sprite` properties and methods are available directly on the group:

```python
group.x, group.y
group.visible
group.flip_x, group.flip_y
group.palette
group.move(dx, dy)
group.move_to(x, y)
group.clamp(x0, y0, x1, y1)
group.collides_with(other)    # accepts SpriteGroup or Sprite
group.on_screen(margin=0)
group.remove()                # unregister sprite from the render list
group.sprite                  # direct access to the underlying Sprite
```

---

## CollisionMap

A 2-D grid of solid / passable flags that shadows a TileMap.
Each cell corresponds to one 8×8 tile. Out-of-bounds cells are always solid.

```python
from pygb import CollisionMap

cmap = CollisionMap(width=32, height=32)
```

### Building the map

```python
# From an existing TileMap — tiles in solid_indices become solid
cmap.from_tilemap(gb.graphics.bg, solid_indices={wall_idx, spike_idx})

# From a 2-D Python list — cells equal to solid_value become solid
LEVEL = [
    [1, 1, 1, 1],
    [1, 0, 0, 1],
    [1, 1, 1, 1],
]
cmap.from_grid(LEVEL, solid_value=1)

# Manual editing
cmap.set(tx, ty, solid=True)
cmap.toggle(tx, ty)
cmap.fill(solid=True)
cmap.fill_rect(tx, ty, w, h, solid=True)
cmap.fill_border()             # mark outermost ring solid
```

### Querying

```python
cmap.get(tx, ty)                      # → bool — is tile cell solid?
cmap.solid_at(px, py)                 # → bool — is the pixel inside a solid cell?
cmap.overlaps_rect(x, y, w, h)        # → bool — does any solid cell overlap this rect?
cmap.solid_sides(x, y, w, h)          # → (left, right, top, bottom) bools
```

### Movement resolution

```python
nx, ny = cmap.resolve(x, y, w, h, dx, dy)
```

Moves a pixel rectangle by `(dx, dy)` and resolves wall collisions with axis-independent sliding (horizontal first).

```python
@gb.on_update
def update():
    global vel_y, on_ground

    dx, _ = gb.input.direction()
    vel_y += 0.3   # gravity

    nx, ny = cmap.resolve(player.x, player.y, 8, 8, dx * 2, vel_y)

    if ny != player.y + vel_y:   # vertical was blocked
        on_ground = (vel_y > 0)
        vel_y = 0

    player.move_to(int(nx), int(ny))
```

### Debugging

```python
cmap.debug_print()   # prints '#' for solid, '.' for passable
print(cmap)          # CollisionMap(32×32, solid=72)
```

### Limitations

- Cells are always 8×8 pixels (one tile). Sub-tile precision requires manual checks.
- `resolve()` does not handle fast-moving objects tunnelling through thin walls. Keep `|dx|` and `|dy|` below 8 pixels per frame.
- The map does not sync automatically when you change the TileMap — call `from_tilemap()` again or update cells manually after runtime changes.

---

## Collision Map Editor

A visual tool for painting solid/passable tiles on a map image. Outputs a JSON file loadable by `CollisionMap`.

### Launch

```bash
# No arguments — opens a startup dialog to pick an image or configure a blank grid
python -m pygb.colli

# Open a tileset / map image directly
python -m pygb.colli <image.png>
python -m pygb.colli <image.png> <output.json>

# Blank grid (no image) — width×height in tiles
python -m pygb.colli --blank 20x18
python -m pygb.colli --blank 32x32 world_collision.json
```

If no output path is given it defaults to `<image_name>_collision.json` (or `collision.json` for blank grids).

### Controls

| Input | Action |
|-------|--------|
| Left click / drag | Mark tiles solid (red overlay) |
| Right click / drag | Mark tiles passable (clear) |
| Middle drag | Pan |
| Scroll wheel | Zoom in / out |
| `S` | Save JSON |
| `Z` | Undo last stroke |
| `R` | Clear all solid tiles |
| `F` | Fill all tiles solid |
| `B` | Fill border solid |
| Escape | Quit |

The status bar turns red when there are unsaved changes.

### JSON format

```json
{
  "cols": 20,
  "rows": 18,
  "data": [[0, 1, 1, 0, ...], ...]
}
```

`0` = passable, `1` = solid. Load it in your game:

```python
from pygb import CollisionMap
import json

with open("map_collision.json") as f:
    saved = json.load(f)

cmap = CollisionMap(saved["cols"], saved["rows"])
cmap.from_grid(saved["data"], solid_value=1)
```

---

## Assets

Load image files and convert them to Tile objects.

```python
from pygb import load_tileset, load_tile

tiles = load_tileset("tileset.png", tile_w=8, tile_h=8, palette=None)
tile  = load_tile("icon.png")
```

`palette` is an optional list of up to 4 RGB tuples used for color matching.
Without it, pixels are quantised to 4 shades by luminance.

```python
from pygb import tiles_from_pixels, surface_to_tile

tiles = tiles_from_pixels(pixel_grid)        # slice a 2-D int grid into tiles
tile  = surface_to_tile(surface, x=0, y=0)  # grab 8×8 from a pygame Surface
```

---

## Utilities

### Timer

```python
from pygb import Timer

t = Timer(frames=30, repeat=True)

if t.tick():    # returns True once every 30 frames
    ...
t.reset()
t.progress      # 0.0 → 1.0 fraction of the current cycle
```

### Rect

```python
from pygb import Rect

r = Rect(x, y, w, h)
r.overlaps(other)       # → bool AABB test
r.contains(px, py)      # → bool point-in-rect test
r.move(dx, dy)          # → new Rect
r.right, r.bottom, r.cx, r.cy
```

### Camera

Tracks a target and updates `graphics.scroll_x/y` each frame.

```python
from pygb import Camera

cam = Camera(gb.graphics, world_w=256, world_h=256,
             screen_w=gb.width, screen_h=gb.height)

@gb.on_update
def update():
    cam.follow(player.x + 4, player.y + 4, smooth=0.15)
```

`screen_w` and `screen_h` default to 160×144. Pass `gb.width`/`gb.height` when using a custom viewport size so the camera centers correctly.

### Animation

Cycles through a list of tile indices at a set frame rate.

```python
from pygb import Animation

anim = Animation(frames=[idle_idx, walk1_idx, walk2_idx], speed=8, loop=True)

@gb.on_update
def update():
    player.tile = gb.graphics.get_tile(anim.update())

anim.reset()
anim.done     # True when a non-looping animation finishes
anim.current  # current frame index without advancing
```

### RNG

Fast LCG pseudo-random number generator.

```python
from pygb import RNG

rng = RNG(seed=0x1234)
rng.randint(0, 9)    # int in [0, 9] inclusive
rng.randf()          # float in [0.0, 1.0)
rng.choice(seq)      # random element from a sequence
rng.next_int()       # raw 16-bit int
```

### Math helpers

```python
from pygb import lerp, clamp, sign

lerp(a, b, t)         # linear interpolation
clamp(value, lo, hi)
sign(x)               # -1, 0, or 1
```

---

## Color Palettes

```python
import pygb.color as color

gb.palette = color.DMG     # classic green LCD (default)
gb.palette = color.GRAY    # grayscale
gb.palette = color.POCKET  # Game Boy Pocket (cooler tones)
gb.palette = color.GBC     # high contrast GBC-style
```

Each palette is a list of 4 `(R, G, B)` tuples ordered lightest → darkest.

---

## Tile Cache

`GameBoy` caches a pygame Surface for every unique (tile, palette, flip, transparency) combination so repeated blits are fast.

```python
gb.clear_tile_cache()   # call after changing palette or editing tile pixel data at runtime
```

---

## Screen Reference

| Property | Value |
|----------|-------|
| Default screen size | 160 × 144 pixels |
| Custom screen size | pass `width`/`height` to `GameBoy()` |
| Tile size | 8 × 8 pixels |
| BG map size | 32 × 32 tiles (256 × 256 pixels, configurable via `TileMap(width, height)`) |
| Color indices | 0 (lightest) — 3 (darkest) |
| Max sprites | 40 |
| Max tiles in VRAM | 256 |

---

## Controls Reference

| Key | GB Button |
|-----|-----------|
| Z / J | A |
| X / K | B |
| Enter | Start |
| RShift / LShift | Select |
| Arrow keys | D-pad |
| W A S D | D-pad (alternate) |
| Escape | Quit |
