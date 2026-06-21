"""PyGB Collision Editor — paint per-tile solid/passable flags on a world image.

Usage:
    python tools/collision_editor.py <image.png> [collision.json]

    If no collision file is given, it defaults to <image>_collision.json.

Controls:
    Left click / drag  — paint solid  (red overlay)
    Right click / drag — erase solid
    Scroll wheel       — zoom in / out
    Arrow keys         — pan the view
    S                  — save
    L                  — load
    C                  — clear all
    G                  — toggle grid
    F                  — toggle reference image (show/hide PNG)
    Escape / Q         — quit
"""

import sys
import os

import pygame
import pygame.freetype

# Allow running from any directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pygb.collision import CollisionMap

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
TILE_PX    = 8          # source tile size in pixels
WIN_W      = 1100
WIN_H      = 720
SIDEBAR_W  = 220        # width of the right-hand control panel
VIEW_W     = WIN_W - SIDEBAR_W
VIEW_H     = WIN_H

BG_COLOR   = (30, 30, 30)
GRID_COLOR = (60, 60, 60)
HOVER_COL  = (255, 255,  80)
SOLID_COL  = (220,  50,  50, 140)   # RGBA
PANEL_COL  = (20, 20, 20)
TEXT_COL   = (200, 200, 200)
SAVE_COL   = (80, 220, 80)

MIN_CELL   = 4
MAX_CELL   = 64


def main():
    # ── Args ──────────────────────────────────
    img_path  = sys.argv[1] if len(sys.argv) > 1 else None
    coll_path = sys.argv[2] if len(sys.argv) > 2 else None

    if img_path and not coll_path:
        coll_path = os.path.splitext(img_path)[0] + "_collision.json"

    # ── Init pygame ───────────────────────────
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("PyGB Collision Editor")
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("monospace", 13)
    font_b = pygame.font.SysFont("monospace", 13, bold=True)

    # ── Load background image ─────────────────
    raw_bg = None
    cols, rows = 32, 32

    if img_path and os.path.exists(img_path):
        raw_bg = pygame.image.load(img_path).convert()
        cols   = raw_bg.get_width()  // TILE_PX
        rows   = raw_bg.get_height() // TILE_PX
    elif img_path:
        print(f"Image not found: {img_path}  — using blank {cols}×{rows} map.")

    # ── Collision map ─────────────────────────
    coll = CollisionMap(cols, rows)
    if coll_path and os.path.exists(coll_path):
        coll = CollisionMap.load(coll_path)
        print(f"Loaded: {coll_path}")

    # ── Editor state ──────────────────────────
    cell_size  = 16       # display pixels per tile
    offset_x   = 0
    offset_y   = 0
    show_grid  = True
    show_bg    = True
    painting   = None     # True = paint solid, False = erase
    save_msg   = ""
    save_timer = 0

    bg_scaled  = None     # cached scaled background

    def rebuild_bg():
        nonlocal bg_scaled
        if raw_bg:
            bg_scaled = pygame.transform.scale(
                raw_bg, (cols * cell_size, rows * cell_size)
            )
        else:
            bg_scaled = None

    def solid_surf():
        s = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
        s.fill(SOLID_COL)
        return s

    rebuild_bg()
    overlay = solid_surf()

    def clamp_offset():
        nonlocal offset_x, offset_y
        max_ox = max(0, cols * cell_size - VIEW_W)
        max_oy = max(0, rows * cell_size - VIEW_H)
        offset_x = max(0, min(offset_x, max_ox))
        offset_y = max(0, min(offset_y, max_oy))

    def screen_to_tile(sx, sy):
        return (sx + offset_x) // cell_size, (sy + offset_y) // cell_size

    def zoom(factor, pivot_sx=None, pivot_sy=None):
        nonlocal cell_size, offset_x, offset_y, overlay
        old = cell_size
        cell_size = max(MIN_CELL, min(MAX_CELL, int(cell_size * factor)))
        if cell_size == old:
            return
        # Keep the tile under the mouse cursor in place
        if pivot_sx is not None:
            tx = (pivot_sx + offset_x) / old
            ty = (pivot_sy + offset_y) / old
            offset_x = int(tx * cell_size - pivot_sx)
            offset_y = int(ty * cell_size - pivot_sy)
        clamp_offset()
        rebuild_bg()
        overlay = solid_surf()

    # ── Sidebar button helper ─────────────────
    buttons = []   # (rect, label, action_key)

    def draw_sidebar():
        nonlocal buttons
        buttons = []
        pygame.draw.rect(screen, PANEL_COL, (VIEW_W, 0, SIDEBAR_W, WIN_H))
        pygame.draw.line(screen, (60, 60, 60), (VIEW_W, 0), (VIEW_W, WIN_H))

        x0 = VIEW_W + 12
        y  = 14

        def heading(text):
            nonlocal y
            surf = font_b.render(text, True, (140, 200, 255))
            screen.blit(surf, (x0, y))
            y += 22

        def key_hint(key, desc):
            nonlocal y
            ks = font_b.render(f"[{key}]", True, (255, 220, 80))
            ds = font.render(f" {desc}", True, TEXT_COL)
            screen.blit(ks, (x0, y))
            screen.blit(ds, (x0 + ks.get_width(), y))
            y += 18

        def divider():
            nonlocal y
            pygame.draw.line(screen, (50, 50, 50), (VIEW_W + 8, y + 4), (WIN_W - 8, y + 4))
            y += 14

        def btn(label, action_key):
            nonlocal y
            r = pygame.Rect(x0, y, SIDEBAR_W - 24, 28)
            hovered = r.collidepoint(*pygame.mouse.get_pos())
            col = (70, 100, 140) if hovered else (45, 55, 70)
            pygame.draw.rect(screen, col, r, border_radius=4)
            pygame.draw.rect(screen, (80, 80, 80), r, 1, border_radius=4)
            ts = font.render(label, True, (230, 230, 230))
            screen.blit(ts, (r.x + (r.w - ts.get_width()) // 2, r.y + (r.h - ts.get_height()) // 2))
            buttons.append((r, action_key))
            y += 36

        heading("COLLISION EDITOR")
        divider()

        heading("Tools")
        key_hint("LClick", "Paint solid")
        key_hint("RClick", "Erase")
        y += 4
        divider()

        heading("View")
        key_hint("Scroll",  "Zoom in/out")
        key_hint("+/-",     "Zoom in/out")
        key_hint("Arrows",  "Pan")
        key_hint("G",       "Toggle grid")
        key_hint("F",       "Toggle image")
        y += 4
        divider()

        heading("File")
        btn("Save  [S]", "save")
        btn("Load  [L]", "load")
        btn("Clear [C]", "clear")
        y += 4
        divider()

        # Stats
        solid_n = sum(coll._data[r2][c2] for r2 in range(rows) for c2 in range(cols))
        heading("Info")
        for line in [
            f"Map:   {cols} × {rows} tiles",
            f"World: {cols*TILE_PX} × {rows*TILE_PX} px",
            f"Solid: {solid_n}",
            f"Open:  {cols*rows - solid_n}",
            f"Zoom:  {cell_size}px/tile",
            f"File:  {os.path.basename(coll_path) if coll_path else '(none)'}",
        ]:
            screen.blit(font.render(line, True, TEXT_COL), (x0, y))
            y += 16

        # Save confirmation
        if save_timer > 0:
            msg = font_b.render(save_msg, True, SAVE_COL)
            screen.blit(msg, (x0, WIN_H - 40))

    # ── Main loop ─────────────────────────────
    running = True
    while running:
        clock.tick(60)
        mx, my = pygame.mouse.get_pos()
        hov_tx, hov_ty = screen_to_tile(mx, my)
        in_view = mx < VIEW_W

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                k = event.key
                if k in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif k == pygame.K_g:
                    show_grid = not show_grid
                elif k == pygame.K_f:
                    show_bg = not show_bg
                elif k == pygame.K_c:
                    coll.clear()
                elif k == pygame.K_s:
                    _do_save()
                elif k == pygame.K_l:
                    _do_load()
                elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    zoom(2.0)
                elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    zoom(0.5)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check sidebar buttons first
                clicked_btn = False
                for r, act in buttons:
                    if r.collidepoint(mx, my):
                        clicked_btn = True
                        if act == "save":   _do_save()
                        elif act == "load": _do_load()
                        elif act == "clear": coll.clear()
                if not clicked_btn and in_view:
                    if event.button == 1:
                        # Toggle: if clicking on solid, erase; else paint
                        painting = not coll.get(hov_tx, hov_ty)
                        coll.set(hov_tx, hov_ty, painting)
                    elif event.button == 3:
                        painting = False
                        coll.set(hov_tx, hov_ty, False)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 3):
                    painting = None

            elif event.type == pygame.MOUSEWHEEL and in_view:
                factor = 2.0 if event.y > 0 else 0.5
                zoom(factor, mx, my)

        # Drag painting
        if painting is not None and in_view:
            coll.set(hov_tx, hov_ty, painting)

        # Arrow key panning
        pan = max(4, cell_size // 2)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  offset_x -= pan
        if keys[pygame.K_RIGHT]: offset_x += pan
        if keys[pygame.K_UP]:    offset_y -= pan
        if keys[pygame.K_DOWN]:  offset_y += pan
        clamp_offset()

        if save_timer > 0:
            save_timer -= 1

        # ── Render ──────────────────────────────
        # Clip drawing to the view area
        screen.set_clip(pygame.Rect(0, 0, VIEW_W, VIEW_H))
        screen.fill(BG_COLOR)

        # Background image
        if show_bg and bg_scaled:
            screen.blit(bg_scaled, (-offset_x, -offset_y))
        elif not bg_scaled:
            # Checkerboard for blank maps
            for ty2 in range(rows):
                sy2 = ty2 * cell_size - offset_y
                if sy2 + cell_size < 0 or sy2 >= VIEW_H: continue
                for tx2 in range(cols):
                    sx2 = tx2 * cell_size - offset_x
                    if sx2 + cell_size < 0 or sx2 >= VIEW_W: continue
                    c = (55, 55, 55) if (tx2 + ty2) % 2 == 0 else (75, 75, 75)
                    pygame.draw.rect(screen, c, (sx2, sy2, cell_size, cell_size))

        # Solid overlays
        for ty2 in range(rows):
            sy2 = ty2 * cell_size - offset_y
            if sy2 + cell_size < 0 or sy2 >= VIEW_H: continue
            for tx2 in range(cols):
                if not coll.get(tx2, ty2): continue
                sx2 = tx2 * cell_size - offset_x
                if sx2 + cell_size < 0 or sx2 >= VIEW_W: continue
                screen.blit(overlay, (sx2, sy2))

        # Grid lines
        if show_grid:
            start_tx = max(0, offset_x // cell_size)
            end_tx   = min(cols, (offset_x + VIEW_W) // cell_size + 2)
            for gx in range(start_tx, end_tx + 1):
                x = gx * cell_size - offset_x
                pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, VIEW_H))

            start_ty = max(0, offset_y // cell_size)
            end_ty   = min(rows, (offset_y + VIEW_H) // cell_size + 2)
            for gy in range(start_ty, end_ty + 1):
                y = gy * cell_size - offset_y
                pygame.draw.line(screen, GRID_COLOR, (0, y), (VIEW_W, y))

        # Hover highlight
        if in_view and 0 <= hov_tx < cols and 0 <= hov_ty < rows:
            hx = hov_tx * cell_size - offset_x
            hy = hov_ty * cell_size - offset_y
            pygame.draw.rect(screen, HOVER_COL, (hx, hy, cell_size, cell_size), 2)
            coord = font.render(f"({hov_tx},{hov_ty})", True, HOVER_COL)
            screen.blit(coord, (hx + cell_size + 2, hy))

        # Remove clip for sidebar
        screen.set_clip(None)
        draw_sidebar()

        pygame.display.flip()

    pygame.quit()


# ──────────────────────────────────────────────
# File helpers (need access to outer-scope vars)
# ──────────────────────────────────────────────
_save_msg_ref  = [""]
_save_timer_ref = [0]

def _do_save():
    # Inject into enclosing scope via the nonlocal trick below
    pass

def _do_load():
    pass


# Re-define main with proper closure access
def main():
    img_path  = sys.argv[1] if len(sys.argv) > 1 else None
    coll_path_default = (
        os.path.splitext(img_path)[0] + "_collision.json"
        if img_path else "collision.json"
    )
    coll_path = sys.argv[2] if len(sys.argv) > 2 else coll_path_default

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("PyGB Collision Editor")
    clock  = pygame.time.Clock()
    font   = pygame.font.SysFont("monospace", 13)
    font_b = pygame.font.SysFont("monospace", 13, bold=True)

    raw_bg = None
    cols, rows = 32, 32

    if img_path and os.path.exists(img_path):
        raw_bg = pygame.image.load(img_path).convert()
        cols   = raw_bg.get_width()  // TILE_PX
        rows   = raw_bg.get_height() // TILE_PX

    coll = CollisionMap(cols, rows)
    if os.path.exists(coll_path):
        coll = CollisionMap.load(coll_path)
        print(f"Loaded collision: {coll_path}")

    cell_size = 16
    offset_x  = 0
    offset_y  = 0
    show_grid = True
    show_bg   = True
    painting  = None
    save_msg  = ""
    save_timer = 0
    bg_scaled  = None

    def rebuild_bg():
        nonlocal bg_scaled
        bg_scaled = (
            pygame.transform.scale(raw_bg, (cols * cell_size, rows * cell_size))
            if raw_bg else None
        )

    def make_overlay():
        s = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
        s.fill(SOLID_COL)
        return s

    rebuild_bg()
    overlay = make_overlay()

    def clamp_offset():
        nonlocal offset_x, offset_y
        offset_x = max(0, min(offset_x, max(0, cols * cell_size - VIEW_W)))
        offset_y = max(0, min(offset_y, max(0, rows * cell_size - VIEW_H)))

    def screen_to_tile(sx, sy):
        return (sx + offset_x) // cell_size, (sy + offset_y) // cell_size

    def zoom(factor, pivot_sx=None, pivot_sy=None):
        nonlocal cell_size, offset_x, offset_y, overlay
        old = cell_size
        new = max(MIN_CELL, min(MAX_CELL, int(cell_size * factor)))
        if new == old:
            return
        if pivot_sx is not None:
            tx = (pivot_sx + offset_x) / old
            ty = (pivot_sy + offset_y) / old
            offset_x = int(tx * new - pivot_sx)
            offset_y = int(ty * new - pivot_sy)
        cell_size = new
        clamp_offset()
        rebuild_bg()
        overlay = make_overlay()

    def do_save():
        nonlocal save_msg, save_timer
        coll.save(coll_path)
        save_msg   = f"Saved  {os.path.basename(coll_path)}"
        save_timer = 180
        print(f"Saved: {coll_path}")

    def do_load():
        nonlocal coll, save_msg, save_timer
        if os.path.exists(coll_path):
            coll = CollisionMap.load(coll_path)
            save_msg   = f"Loaded {os.path.basename(coll_path)}"
            save_timer = 180
            print(f"Loaded: {coll_path}")
        else:
            save_msg   = "No file to load"
            save_timer = 120

    # Sidebar button list populated each frame
    buttons = []

    def draw_sidebar():
        nonlocal buttons
        buttons = []
        pygame.draw.rect(screen, PANEL_COL, (VIEW_W, 0, SIDEBAR_W, WIN_H))
        pygame.draw.line(screen, (55, 55, 55), (VIEW_W, 0), (VIEW_W, WIN_H))

        x0 = VIEW_W + 12
        y  = [14]

        def heading(text):
            screen.blit(font_b.render(text, True, (120, 180, 255)), (x0, y[0]))
            y[0] += 22

        def hint(key, desc):
            ks = font_b.render(f"[{key}]", True, (255, 210, 60))
            ds = font.render(f" {desc}", True, TEXT_COL)
            screen.blit(ks, (x0, y[0]))
            screen.blit(ds, (x0 + ks.get_width(), y[0]))
            y[0] += 18

        def line():
            pygame.draw.line(screen, (50,50,50), (VIEW_W+6, y[0]+4), (WIN_W-6, y[0]+4))
            y[0] += 14

        def btn(label, key):
            r = pygame.Rect(x0, y[0], SIDEBAR_W - 24, 30)
            hov = r.collidepoint(*pygame.mouse.get_pos())
            pygame.draw.rect(screen, (65,95,130) if hov else (42,52,65), r, border_radius=5)
            pygame.draw.rect(screen, (80,80,80), r, 1, border_radius=5)
            ts = font.render(label, True, (230,230,230))
            screen.blit(ts, (r.x + (r.w-ts.get_width())//2, r.y + (r.h-ts.get_height())//2))
            buttons.append((r, key))
            y[0] += 38

        heading("COLLISION EDITOR")
        line()
        heading("Paint")
        hint("L-Click", "paint solid")
        hint("R-Click", "erase")
        y[0] += 4
        line()
        heading("View")
        hint("Scroll",  "zoom")
        hint("+  /  -", "zoom")
        hint("Arrows",  "pan")
        hint("G",       "toggle grid")
        hint("F",       "toggle image")
        y[0] += 4
        line()
        heading("File")
        btn("Save  [S]", "save")
        btn("Load  [L]", "load")
        btn("Clear [C]", "clear")
        y[0] += 4
        line()
        heading("Info")
        solid_n = sum(coll._data[r2][c2] for r2 in range(rows) for c2 in range(cols))
        for info in [
            f"Map :  {cols} × {rows} tiles",
            f"World: {cols*TILE_PX} × {rows*TILE_PX} px",
            f"Solid: {solid_n}",
            f"Open : {cols*rows - solid_n}",
            f"Zoom : {cell_size}px / tile",
            f"File : {os.path.basename(coll_path)}",
        ]:
            screen.blit(font.render(info, True, TEXT_COL), (x0, y[0]))
            y[0] += 16

        if save_timer > 0:
            alpha = min(255, save_timer * 4)
            msg_col = (80, min(255, alpha), 80)
            screen.blit(font_b.render(save_msg, True, msg_col), (x0, WIN_H - 36))

    # ── Main loop ─────────────────────────────
    running = True
    while running:
        clock.tick(60)
        mx, my   = pygame.mouse.get_pos()
        in_view  = mx < VIEW_W
        hov_tx, hov_ty = screen_to_tile(mx, my)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                k = event.key
                if   k in (pygame.K_ESCAPE, pygame.K_q): running = False
                elif k == pygame.K_g:                      show_grid = not show_grid
                elif k == pygame.K_f:                      show_bg   = not show_bg
                elif k == pygame.K_c:                      coll.clear()
                elif k == pygame.K_s:                      do_save()
                elif k == pygame.K_l:                      do_load()
                elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):  zoom(2.0)
                elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):                 zoom(0.5)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                handled = False
                for r, act in buttons:
                    if r.collidepoint(mx, my):
                        handled = True
                        if   act == "save":  do_save()
                        elif act == "load":  do_load()
                        elif act == "clear": coll.clear()
                if not handled and in_view:
                    if event.button == 1:
                        painting = not coll.get(hov_tx, hov_ty)
                        coll.set(hov_tx, hov_ty, painting)
                    elif event.button == 3:
                        painting = False
                        coll.set(hov_tx, hov_ty, False)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (1, 3):
                    painting = None

            elif event.type == pygame.MOUSEWHEEL and in_view:
                zoom(2.0 if event.y > 0 else 0.5, mx, my)

        # Continue drag-painting
        if painting is not None and in_view:
            coll.set(hov_tx, hov_ty, painting)

        # Arrow panning
        pan = max(4, cell_size // 2)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:  offset_x -= pan
        if keys[pygame.K_RIGHT]: offset_x += pan
        if keys[pygame.K_UP]:    offset_y -= pan
        if keys[pygame.K_DOWN]:  offset_y += pan
        clamp_offset()

        if save_timer > 0:
            save_timer -= 1

        # ── Render view ───────────────────────
        screen.set_clip(pygame.Rect(0, 0, VIEW_W, VIEW_H))
        screen.fill(BG_COLOR)

        if show_bg and bg_scaled:
            screen.blit(bg_scaled, (-offset_x, -offset_y))
        elif not raw_bg:
            for ty2 in range(rows):
                sy2 = ty2 * cell_size - offset_y
                if sy2 + cell_size < 0 or sy2 >= VIEW_H: continue
                for tx2 in range(cols):
                    sx2 = tx2 * cell_size - offset_x
                    if sx2 + cell_size < 0 or sx2 >= VIEW_W: continue
                    c = (52,52,52) if (tx2+ty2)%2==0 else (72,72,72)
                    pygame.draw.rect(screen, c, (sx2, sy2, cell_size, cell_size))

        # Solid overlays
        for ty2 in range(rows):
            sy2 = ty2 * cell_size - offset_y
            if sy2 + cell_size < 0 or sy2 >= VIEW_H: continue
            for tx2 in range(cols):
                if not coll.get(tx2, ty2): continue
                sx2 = tx2 * cell_size - offset_x
                if sx2 + cell_size < 0 or sx2 >= VIEW_W: continue
                screen.blit(overlay, (sx2, sy2))

        # Grid
        if show_grid:
            stx = max(0, offset_x // cell_size)
            etx = min(cols, (offset_x + VIEW_W) // cell_size + 2)
            for gx in range(stx, etx + 1):
                x = gx * cell_size - offset_x
                pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, VIEW_H))
            sty = max(0, offset_y // cell_size)
            ety = min(rows, (offset_y + VIEW_H) // cell_size + 2)
            for gy in range(sty, ety + 1):
                y = gy * cell_size - offset_y
                pygame.draw.line(screen, GRID_COLOR, (0, y), (VIEW_W, y))

        # Hover
        if in_view and 0 <= hov_tx < cols and 0 <= hov_ty < rows:
            hx = hov_tx * cell_size - offset_x
            hy = hov_ty * cell_size - offset_y
            pygame.draw.rect(screen, HOVER_COL, (hx, hy, cell_size, cell_size), 2)
            screen.blit(
                font.render(f"({hov_tx},{hov_ty})", True, HOVER_COL),
                (max(0, hx + cell_size + 2), hy),
            )

        screen.set_clip(None)
        draw_sidebar()
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
