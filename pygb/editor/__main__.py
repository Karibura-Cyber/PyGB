"""PyGB Collision Map Editor.

Usage:
    python -m pygb.editor <image.png> [output.json]
    python -m pygb.editor <map.tmx>   [output.json]

Controls:
    Left click / drag   — mark tiles solid   (red)
    Right click / drag  — mark tiles passable (clear)
    Middle drag         — pan
    Scroll up/down      — zoom in / out
    S                   — save
    R                   — clear all solid tiles
    Z                   — undo last stroke
    Escape              — quit
"""

import sys
import os
import json

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _usage():
    print("Usage: python -m pygb.editor <image.png|map.tmx> [output.json]")
    print()
    print("  Left click / drag    mark tiles solid")
    print("  Right click / drag   mark tiles passable")
    print("  Middle drag          pan")
    print("  Scroll               zoom in / out")
    print("  S                    save")
    print("  R                    clear all")
    print("  Z                    undo last paint stroke")
    print("  Escape               quit")

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help"):
        _usage()
        sys.exit(0)

    src_path = argv[0]
    if not os.path.exists(src_path):
        print(f"Error: file not found: {src_path!r}")
        sys.exit(1)

    base     = os.path.splitext(src_path)[0]
    out_path = argv[1] if len(argv) > 1 else base + "_collision.json"

    if src_path.lower().endswith(".tmx"):
        surf, tile_size = _render_tmx(src_path)
        _run_editor(src_path, out_path, src_surf=surf, tile_size=tile_size)
    else:
        _run_editor(src_path, out_path)


# ---------------------------------------------------------------------------
# TMX renderer — flatten all tile layers into one pygame.Surface
# ---------------------------------------------------------------------------

def _render_tmx(tmx_path: str):
    """Render all tile layers of a TMX map into a single Surface.

    Returns:
        (surface, tile_size) — the composed map image and the tile size in px.
    """
    try:
        import pytmx
    except ImportError:
        print("Error: pytmx is required for TMX support: pip install pytmx")
        sys.exit(1)

    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))   # minimal display needed for convert()

    tiled_map = pytmx.load_pygame(tmx_path)
    ts  = tiled_map.tilewidth
    mw  = tiled_map.width  * ts
    mh  = tiled_map.height * ts

    surf = pygame.Surface((mw, mh))
    surf.fill((0, 0, 0))

    for layer in tiled_map.layers:
        if not isinstance(layer, pytmx.TiledTileLayer):
            continue
        for x, y, gid in layer:
            if gid == 0:
                continue
            tile_surf = tiled_map.get_tile_image_by_gid(gid)
            if tile_surf:
                surf.blit(tile_surf, (x * ts, y * ts))

    return surf, ts


# ---------------------------------------------------------------------------
# Editor
# ---------------------------------------------------------------------------

STATUS_H = 30
BG      = (24, 24, 36)
BAR_BG  = (16, 16, 30)
BAR_FG  = (180, 210, 255)
SOLID   = (220,  50,  50, 130)   # semi-transparent red overlay
GRID    = ( 80, 160, 255,  50)   # semi-transparent blue grid lines


def _run_editor(
    src_path: str,
    out_path: str,
    src_surf=None,      # pre-rendered surface (used for TMX input)
    tile_size: int = 8,
) -> None:
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((960, 680), pygame.RESIZABLE)
    pygame.display.set_caption(
        f"PyGB Collision Editor — {os.path.basename(src_path)}"
    )
    clock = pygame.time.Clock()

    try:
        font = pygame.font.SysFont("consolas,monospace", 14)
    except Exception:
        font = pygame.font.Font(None, 18)

    # --- Load / use image ----------------------------------------------------
    if src_surf is not None:
        src_img = src_surf.convert()
    else:
        src_img = pygame.image.load(src_path).convert()

    img_w, img_h = src_img.get_size()
    TILE = tile_size
    cols = img_w // TILE
    rows = img_h // TILE

    if cols == 0 or rows == 0:
        print(f"Error: image ({img_w}×{img_h}) is smaller than one tile ({TILE}px)")
        pygame.quit()
        sys.exit(1)

    # --- Collision grid -------------------------------------------------------
    grid = [[False] * cols for _ in range(rows)]

    if os.path.exists(out_path):
        try:
            with open(out_path) as f:
                saved = json.load(f)
            for ty, row in enumerate(saved.get("data", [])):
                for tx, val in enumerate(row):
                    if ty < rows and tx < cols:
                        grid[ty][tx] = bool(val)
            print(f"Loaded existing collision: {out_path}")
        except Exception as e:
            print(f"Warning: could not load {out_path}: {e}")

    # --- Zoom + pan -----------------------------------------------------------
    sw, sh = screen.get_size()
    zoom = max(1, min(8, int(min(
        (sw - 20) / img_w,
        (sh - STATUS_H - 20) / img_h,
    ))))
    offset_x = (sw - img_w * zoom) // 2
    offset_y = (sh - STATUS_H - img_h * zoom) // 2

    # --- Cached scaled surfaces -----------------------------------------------
    scaled_img  = None
    solid_surf  = None
    grid_surf   = None

    def rebuild(new_zoom: int) -> None:
        nonlocal scaled_img, solid_surf, grid_surf, zoom
        zoom = new_zoom
        W, H = img_w * zoom, img_h * zoom

        scaled_img = pygame.transform.scale(src_img, (W, H))

        solid_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        solid_surf.fill((0, 0, 0, 0))
        for ty in range(rows):
            for tx in range(cols):
                if grid[ty][tx]:
                    solid_surf.fill(SOLID, _tile_rect(tx, ty))

        grid_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        for tx in range(cols + 1):
            x = tx * TILE * zoom
            pygame.draw.line(grid_surf, GRID, (x, 0), (x, H))
        for ty in range(rows + 1):
            y = ty * TILE * zoom
            pygame.draw.line(grid_surf, GRID, (0, y), (W, y))

    def _tile_rect(tx: int, ty: int):
        return (tx * TILE * zoom, ty * TILE * zoom, TILE * zoom, TILE * zoom)

    def screen_to_tile(mx: int, my: int):
        return (mx - offset_x) // (TILE * zoom), (my - offset_y) // (TILE * zoom)

    def mark(tx: int, ty: int, solid: bool) -> bool:
        """Set one tile; returns True if the value changed."""
        if 0 <= tx < cols and 0 <= ty < rows and grid[ty][tx] != solid:
            grid[ty][tx] = solid
            r = _tile_rect(tx, ty)
            if solid:
                solid_surf.fill(SOLID, r)
            else:
                solid_surf.fill((0, 0, 0, 0), r)
            return True
        return False

    def save() -> None:
        data = {
            "cols": cols,
            "rows": rows,
            "data": [
                [1 if grid[ty][tx] else 0 for tx in range(cols)]
                for ty in range(rows)
            ],
        }
        with open(out_path, "w") as f:
            json.dump(data, f)
        print(f"Saved → {out_path}")

    rebuild(zoom)

    # --- Undo stack (list of grid snapshots before each stroke) ---------------
    undo_stack = []

    def push_undo():
        undo_stack.append([row[:] for row in grid])
        if len(undo_stack) > 50:
            undo_stack.pop(0)

    def do_undo():
        if not undo_stack:
            return
        snap = undo_stack.pop()
        for ty in range(rows):
            for tx in range(cols):
                grid[ty][tx] = snap[ty][tx]
        # Rebuild solid overlay from restored grid
        solid_surf.fill((0, 0, 0, 0))
        for ty in range(rows):
            for tx in range(cols):
                if grid[ty][tx]:
                    solid_surf.fill(SOLID, _tile_rect(tx, ty))

    # --- Main loop -----------------------------------------------------------
    painting  = False
    erasing   = False
    panning   = False
    pan_start = (0, 0)
    pan_origin = (0, 0)
    unsaved   = False

    running = True
    while running:
        sw, sh = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_s:
                    save()
                    unsaved = False
                elif event.key == pygame.K_z and (mods & pygame.KMOD_CTRL or True):
                    do_undo()
                    unsaved = True
                    # Rebuild after undo
                    solid_surf.fill((0, 0, 0, 0))
                    for ty in range(rows):
                        for tx in range(cols):
                            if grid[ty][tx]:
                                solid_surf.fill(SOLID, _tile_rect(tx, ty))
                elif event.key == pygame.K_r:
                    push_undo()
                    for ty in range(rows):
                        for tx in range(cols):
                            grid[ty][tx] = False
                    solid_surf.fill((0, 0, 0, 0))
                    unsaved = True

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if event.button == 1:
                    push_undo()
                    painting = True
                    mark(*screen_to_tile(mx, my), True)
                    unsaved = True
                elif event.button == 3:
                    push_undo()
                    erasing = True
                    mark(*screen_to_tile(mx, my), False)
                    unsaved = True
                elif event.button == 2:
                    panning = True
                    pan_start  = event.pos
                    pan_origin = (offset_x, offset_y)
                elif event.button in (4, 5):
                    old_zoom = zoom
                    new_zoom = min(8, zoom + 1) if event.button == 4 else max(1, zoom - 1)
                    if new_zoom != old_zoom:
                        rebuild(new_zoom)
                        # Zoom toward mouse position
                        offset_x = mx - (mx - offset_x) * new_zoom // old_zoom
                        offset_y = my - (my - offset_y) * new_zoom // old_zoom

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1: painting = False
                if event.button == 3: erasing  = False
                if event.button == 2: panning  = False

            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                if painting:
                    mark(*screen_to_tile(mx, my), True)
                    unsaved = True
                if erasing:
                    mark(*screen_to_tile(mx, my), False)
                    unsaved = True
                if panning:
                    offset_x = pan_origin[0] + mx - pan_start[0]
                    offset_y = pan_origin[1] + my - pan_start[1]

        # Draw ----------------------------------------------------------------
        screen.fill(BG)
        screen.blit(scaled_img, (offset_x, offset_y))
        screen.blit(solid_surf,  (offset_x, offset_y))
        screen.blit(grid_surf,   (offset_x, offset_y))

        # Hover highlight
        mx, my = pygame.mouse.get_pos()
        htx, hty = screen_to_tile(mx, my)
        if 0 <= htx < cols and 0 <= hty < rows:
            hr = pygame.Rect(
                offset_x + htx * TILE * zoom,
                offset_y + hty * TILE * zoom,
                TILE * zoom, TILE * zoom,
            )
            pygame.draw.rect(screen, (255, 255, 100), hr, 2)

        # Status bar
        solid_count = sum(grid[ty][tx] for ty in range(rows) for tx in range(cols))
        status = (
            f"  {os.path.basename(src_path)}  |  "
            f"{cols}×{rows} tiles  |  "
            f"cursor ({htx},{hty})  |  "
            f"solid: {solid_count}  |  "
            f"zoom: {zoom}×  |  "
            + ("*unsaved*  " if unsaved else "saved  ")
            + "[S] save  [Z] undo  [R] clear  [scroll] zoom  [MMB] pan  [Esc] quit"
        )
        bar = pygame.Surface((sw, STATUS_H))
        bar.fill(BAR_BG)
        bar.blit(font.render(status, True, BAR_FG), (6, 8))
        screen.blit(bar, (0, sh - STATUS_H))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
