"""PyGB Collision Map Editor.

Usage:
    python -m pygb.colli                         # launch startup dialog
    python -m pygb.colli <image.png>             # open image directly
    python -m pygb.colli <image.png> <out.json>  # open image, save to specific file
    python -m pygb.colli --blank WxH             # blank W×H tile map  (e.g. 20x18)
    python -m pygb.colli --blank WxH <out.json>

Controls (in editor):
    Left click / drag   — mark tiles solid   (red)
    Right click / drag  — mark tiles passable (clear)
    Middle drag         — pan
    Scroll              — zoom in / out
    S                   — save
    Z                   — undo last stroke
    R                   — clear all solid tiles
    F                   — fill all tiles solid
    B                   — fill border solid
    Escape              — quit
"""

import sys
import os
import json


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TILE      = 8          # pixels per tile
STATUS_H  = 32
BG_COL    = (24, 24, 36)
BAR_BG    = (16, 16, 30)
BAR_FG    = (180, 210, 255)
SOLID_COL = (220, 50,  50, 140)
GRID_COL  = (80,  160, 255, 45)
BLANK_BG  = (40,  44,  52)   # tile background for blank (no-image) maps
BLANK_FG  = (55,  60,  72)   # alternating tile shade


# ---------------------------------------------------------------------------
# Startup dialog (tkinter)
# ---------------------------------------------------------------------------

def _startup_dialog():
    """Show a startup dialog.  Returns (img_path_or_None, cols, rows, out_path)."""
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox
    except ImportError:
        print("tkinter not available — pass arguments on the command line.")
        print("  python -m pygb.colli <image.png> [out.json]")
        print("  python -m pygb.colli --blank 20x18 [out.json]")
        sys.exit(1)

    result = {}

    root = tk.Tk()
    root.title("PyGB Collision Editor — Open")
    root.resizable(False, False)

    # ── header ───────────────────────────────────────────────────────────────
    hdr = tk.Frame(root, bg="#1a1a2e", padx=16, pady=12)
    hdr.pack(fill="x")
    tk.Label(hdr, text="PyGB Collision Map Editor",
             font=("Segoe UI", 13, "bold"),
             fg="#b0d0ff", bg="#1a1a2e").pack(anchor="w")
    tk.Label(hdr, text="Paint solid tiles on a tileset image or start with a blank grid.",
             font=("Segoe UI", 9),
             fg="#7090b0", bg="#1a1a2e").pack(anchor="w")

    body = tk.Frame(root, padx=20, pady=16, bg="#16213e")
    body.pack(fill="both", expand=True)

    # ── mode tabs ─────────────────────────────────────────────────────────────
    mode_var = tk.StringVar(value="image")

    tab_frame = tk.Frame(body, bg="#16213e")
    tab_frame.pack(fill="x", pady=(0, 12))

    def make_tab(text, value, col):
        btn = tk.Radiobutton(
            tab_frame, text=text, variable=mode_var, value=value,
            font=("Segoe UI", 10), indicator=0,
            bg="#0f3460", fg="#b0d0ff", selectcolor="#e94560",
            activebackground="#e94560", activeforeground="white",
            padx=14, pady=6, relief="flat", cursor="hand2",
            command=_refresh,
        )
        btn.grid(row=0, column=col, padx=(0, 4))

    make_tab("Open Image", "image", 0)
    make_tab("Blank Grid", "blank", 1)

    # ── image section ─────────────────────────────────────────────────────────
    img_frame = tk.LabelFrame(body, text=" Image File ", padx=12, pady=10,
                               bg="#16213e", fg="#7090b0",
                               font=("Segoe UI", 9))
    img_frame.pack(fill="x", pady=(0, 8))

    img_path_var = tk.StringVar()
    img_row = tk.Frame(img_frame, bg="#16213e")
    img_row.pack(fill="x")
    tk.Entry(img_row, textvariable=img_path_var, width=36,
             bg="#0d1b2a", fg="#c0d8ff", insertbackground="white",
             relief="flat", font=("Consolas", 9)).pack(side="left", fill="x", expand=True)
    def _browse():
        p = filedialog.askopenfilename(
            title="Select tileset / map image",
            filetypes=[("PNG images", "*.png"), ("All files", "*.*")]
        )
        if p:
            img_path_var.set(p)
    tk.Button(img_row, text="Browse…", command=_browse,
              bg="#0f3460", fg="#b0d0ff", relief="flat",
              padx=8, cursor="hand2").pack(side="left", padx=(6, 0))

    # ── blank section ─────────────────────────────────────────────────────────
    blank_frame = tk.LabelFrame(body, text=" Blank Grid Size (tiles) ", padx=12, pady=10,
                                 bg="#16213e", fg="#7090b0",
                                 font=("Segoe UI", 9))
    blank_frame.pack(fill="x", pady=(0, 8))

    sz_row = tk.Frame(blank_frame, bg="#16213e")
    sz_row.pack()
    tk.Label(sz_row, text="Width:", bg="#16213e", fg="#b0d0ff",
             font=("Segoe UI", 9)).pack(side="left")
    cols_var = tk.IntVar(value=20)
    tk.Spinbox(sz_row, from_=1, to=256, textvariable=cols_var, width=5,
               bg="#0d1b2a", fg="#c0d8ff", buttonbackground="#0f3460",
               relief="flat", font=("Consolas", 10)).pack(side="left", padx=(4, 12))
    tk.Label(sz_row, text="Height:", bg="#16213e", fg="#b0d0ff",
             font=("Segoe UI", 9)).pack(side="left")
    rows_var = tk.IntVar(value=18)
    tk.Spinbox(sz_row, from_=1, to=256, textvariable=rows_var, width=5,
               bg="#0d1b2a", fg="#c0d8ff", buttonbackground="#0f3460",
               relief="flat", font=("Consolas", 10)).pack(side="left", padx=(4, 0))

    # ── output file ───────────────────────────────────────────────────────────
    out_frame = tk.LabelFrame(body, text=" Output JSON (optional) ", padx=12, pady=10,
                               bg="#16213e", fg="#7090b0",
                               font=("Segoe UI", 9))
    out_frame.pack(fill="x", pady=(0, 12))

    out_path_var = tk.StringVar()
    out_row = tk.Frame(out_frame, bg="#16213e")
    out_row.pack(fill="x")
    tk.Entry(out_row, textvariable=out_path_var, width=36,
             bg="#0d1b2a", fg="#c0d8ff", insertbackground="white",
             relief="flat", font=("Consolas", 9)).pack(side="left", fill="x", expand=True)
    def _browse_out():
        p = filedialog.asksaveasfilename(
            title="Save collision JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if p:
            out_path_var.set(p)
    tk.Button(out_row, text="Browse…", command=_browse_out,
              bg="#0f3460", fg="#b0d0ff", relief="flat",
              padx=8, cursor="hand2").pack(side="left", padx=(6, 0))

    # ── toggle visibility ─────────────────────────────────────────────────────
    def _refresh():
        mode = mode_var.get()
        if mode == "image":
            img_frame.pack(fill="x", pady=(0, 8), before=blank_frame)
        else:
            img_frame.pack_forget()

    _refresh()

    # ── buttons ───────────────────────────────────────────────────────────────
    btn_row = tk.Frame(body, bg="#16213e")
    btn_row.pack(fill="x")

    def _ok():
        mode = mode_var.get()
        if mode == "image":
            ip = img_path_var.get().strip()
            if not ip:
                messagebox.showerror("Error", "Please select an image file.")
                return
            if not os.path.exists(ip):
                messagebox.showerror("Error", f"File not found:\n{ip}")
                return
            result["img"] = ip
            result["cols"] = None
            result["rows"] = None
        else:
            result["img"] = None
            result["cols"] = int(cols_var.get())
            result["rows"] = int(rows_var.get())

        op = out_path_var.get().strip()
        result["out"] = op if op else None
        root.destroy()

    def _cancel():
        sys.exit(0)

    tk.Button(btn_row, text="Open Editor", command=_ok,
              bg="#e94560", fg="white", relief="flat",
              font=("Segoe UI", 10, "bold"), padx=16, pady=6,
              cursor="hand2").pack(side="right")
    tk.Button(btn_row, text="Cancel", command=_cancel,
              bg="#0f3460", fg="#b0d0ff", relief="flat",
              padx=12, pady=6, cursor="hand2").pack(side="right", padx=(0, 8))

    root.configure(bg="#16213e")
    root.mainloop()

    if not result:
        sys.exit(0)
    return result.get("img"), result.get("cols"), result.get("rows"), result.get("out")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args(argv):
    """Returns (img_path_or_None, cols_or_None, rows_or_None, out_path_or_None)."""
    if not argv:
        return _startup_dialog()

    if argv[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    if argv[0] == "--blank":
        if len(argv) < 2:
            print("Error: --blank requires WxH  (e.g. --blank 20x18)")
            sys.exit(1)
        try:
            w_str, h_str = argv[1].lower().split("x")
            cols, rows = int(w_str), int(h_str)
        except ValueError:
            print(f"Error: invalid size {argv[1]!r} — expected WxH like 20x18")
            sys.exit(1)
        out = argv[2] if len(argv) > 2 else None
        return None, cols, rows, out

    img_path = argv[0]
    if not os.path.exists(img_path):
        print(f"Error: file not found: {img_path!r}")
        sys.exit(1)
    out = argv[1] if len(argv) > 1 else None
    return img_path, None, None, out


# ---------------------------------------------------------------------------
# Pygame editor
# ---------------------------------------------------------------------------

def _run_editor(img_path, cols, rows, out_path):
    import pygame

    # ── derive grid size & output path ────────────────────────────────────────
    if img_path:
        tmp = pygame.image.load(img_path)
        iw, ih = tmp.get_size()
        if cols is None:
            cols = max(1, iw // TILE)
        if rows is None:
            rows = max(1, ih // TILE)
        if out_path is None:
            out_path = os.path.splitext(img_path)[0] + "_collision.json"
        title_name = os.path.basename(img_path)
    else:
        if out_path is None:
            out_path = "collision.json"
        title_name = f"blank {cols}×{rows}"

    # ── init ──────────────────────────────────────────────────────────────────
    pygame.init()
    screen = pygame.display.set_mode((960, 680), pygame.RESIZABLE)
    pygame.display.set_caption(f"PyGB Collision Editor — {title_name}")
    clock = pygame.time.Clock()

    try:
        font = pygame.font.SysFont("consolas,monospace", 13)
    except Exception:
        font = pygame.font.Font(None, 16)

    # ── source image or blank ─────────────────────────────────────────────────
    if img_path:
        src_img = pygame.image.load(img_path).convert()
        img_w, img_h = src_img.get_size()
    else:
        img_w, img_h = cols * TILE, rows * TILE
        src_img = pygame.Surface((img_w, img_h))
        # Draw checkerboard-style blank background
        for ty in range(rows):
            for tx in range(cols):
                shade = BLANK_FG if (tx + ty) % 2 == 0 else BLANK_BG
                src_img.fill(shade, (tx * TILE, ty * TILE, TILE, TILE))

    # ── collision grid ────────────────────────────────────────────────────────
    grid = [[False] * cols for _ in range(rows)]

    if os.path.exists(out_path):
        try:
            with open(out_path) as f:
                saved = json.load(f)
            for ty, row in enumerate(saved.get("data", [])):
                for tx, val in enumerate(row):
                    if ty < rows and tx < cols:
                        grid[ty][tx] = bool(val)
            print(f"Loaded: {out_path}")
        except Exception as e:
            print(f"Warning: could not load {out_path}: {e}")

    # ── zoom + pan ────────────────────────────────────────────────────────────
    sw, sh = screen.get_size()
    zoom = max(1, min(8, int(min(
        (sw - 20) / img_w,
        (sh - STATUS_H - 20) / img_h,
    ))))
    offset_x = (sw - img_w * zoom) // 2
    offset_y = (sh - STATUS_H - img_h * zoom) // 2

    # ── cached surfaces ───────────────────────────────────────────────────────
    scaled_img  = None
    solid_surf  = None
    grid_surf   = None

    def _tile_rect(tx, ty):
        return (tx * TILE * zoom, ty * TILE * zoom, TILE * zoom, TILE * zoom)

    def rebuild(new_zoom):
        nonlocal scaled_img, solid_surf, grid_surf, zoom
        zoom = new_zoom
        W, H = img_w * zoom, img_h * zoom

        scaled_img = pygame.transform.scale(src_img, (W, H))

        solid_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        solid_surf.fill((0, 0, 0, 0))
        for ty in range(rows):
            for tx in range(cols):
                if grid[ty][tx]:
                    solid_surf.fill(SOLID_COL, _tile_rect(tx, ty))

        grid_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        grid_surf.fill((0, 0, 0, 0))
        for tx in range(cols + 1):
            x = tx * TILE * zoom
            pygame.draw.line(grid_surf, GRID_COL, (x, 0), (x, H))
        for ty in range(rows + 1):
            y = ty * TILE * zoom
            pygame.draw.line(grid_surf, GRID_COL, (0, y), (W, y))

    rebuild(zoom)

    # ── helpers ───────────────────────────────────────────────────────────────
    def screen_to_tile(mx, my):
        return (mx - offset_x) // (TILE * zoom), (my - offset_y) // (TILE * zoom)

    def mark(tx, ty, solid):
        if 0 <= tx < cols and 0 <= ty < rows and grid[ty][tx] != solid:
            grid[ty][tx] = solid
            r = _tile_rect(tx, ty)
            solid_surf.fill(SOLID_COL if solid else (0, 0, 0, 0), r)
            return True
        return False

    def solid_count():
        return sum(grid[ty][tx] for ty in range(rows) for tx in range(cols))

    def save():
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

    # ── undo stack ────────────────────────────────────────────────────────────
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
        solid_surf.fill((0, 0, 0, 0))
        for ty in range(rows):
            for tx in range(cols):
                if grid[ty][tx]:
                    solid_surf.fill(SOLID_COL, _tile_rect(tx, ty))

    def rebuild_solid():
        solid_surf.fill((0, 0, 0, 0))
        for ty in range(rows):
            for tx in range(cols):
                if grid[ty][tx]:
                    solid_surf.fill(SOLID_COL, _tile_rect(tx, ty))

    # ── main loop ─────────────────────────────────────────────────────────────
    painting  = False
    erasing   = False
    panning   = False
    pan_start  = (0, 0)
    pan_origin = (0, 0)
    unsaved   = False
    running   = True

    while running:
        sw, sh = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_s:
                    save()
                    unsaved = False

                elif event.key == pygame.K_z:
                    push_undo()   # save current before undo so we can re-do manually
                    do_undo()
                    rebuild_solid()
                    unsaved = True

                elif event.key == pygame.K_r:
                    push_undo()
                    for row in grid:
                        for tx in range(cols): row[tx] = False
                    rebuild_solid()
                    unsaved = True

                elif event.key == pygame.K_f:
                    push_undo()
                    for row in grid:
                        for tx in range(cols): row[tx] = True
                    rebuild_solid()
                    unsaved = True

                elif event.key == pygame.K_b:
                    push_undo()
                    for tx in range(cols):
                        grid[0][tx] = True
                        grid[rows - 1][tx] = True
                    for ty in range(rows):
                        grid[ty][0] = True
                        grid[ty][cols - 1] = True
                    rebuild_solid()
                    unsaved = True

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if my >= sh - STATUS_H:
                    pass  # ignore status bar clicks
                elif event.button == 1:
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
                        mx, my = event.pos
                        rebuild(new_zoom)
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

            elif event.type == pygame.VIDEORESIZE:
                sw, sh = event.size
                screen = pygame.display.set_mode((sw, sh), pygame.RESIZABLE)

        # ── draw ──────────────────────────────────────────────────────────────
        screen.fill(BG_COL)
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
            pygame.draw.rect(screen, (255, 255, 80), hr, max(1, zoom // 2))

        # ── status bar ────────────────────────────────────────────────────────
        sc = solid_count()
        cursor_str = f"({htx},{hty})" if 0 <= htx < cols and 0 <= hty < rows else "---"
        tile_state = "SOLID" if (0 <= htx < cols and 0 <= hty < rows and grid[hty][htx]) else "open"
        save_flag  = "*UNSAVED*" if unsaved else "saved"
        parts = [
            f" {title_name}",
            f"{cols}×{rows} tiles",
            f"solid: {sc}/{cols*rows}",
            f"cursor: {cursor_str} [{tile_state}]",
            f"zoom: {zoom}×",
            save_flag,
            "[S] save  [Z] undo  [R] clear  [F] fill  [B] border  [scroll] zoom  [MMB] pan  [Esc] quit",
        ]
        status = "  |  ".join(parts)

        bar = pygame.Surface((sw, STATUS_H))
        bar.fill(BAR_BG)
        # Colored indicator strip
        bar.fill((220, 50, 50) if unsaved else (50, 180, 80), (0, 0, 4, STATUS_H))
        bar.blit(font.render(status, True, BAR_FG), (10, (STATUS_H - font.get_height()) // 2))
        screen.blit(bar, (0, sh - STATUS_H))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    img_path, cols, rows, out_path = _parse_args(sys.argv[1:])

    import pygame
    pygame.init()

    _run_editor(img_path, cols, rows, out_path)


if __name__ == "__main__":
    main()
