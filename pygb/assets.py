"""Asset loading — convert PNG/image files into Tile objects."""

from __future__ import annotations
from typing import List, Optional, Sequence, Tuple

from .tile import Tile

Color = Tuple[int, int, int]


def _rgb_to_gb(rgb: Color, palette: Optional[List[Color]]) -> int:
    """Map an RGB color to a GB color index (0–3)."""
    if palette:
        best, best_dist = 0, float("inf")
        for i, pc in enumerate(palette[:4]):
            dist = sum((a - b) ** 2 for a, b in zip(rgb, pc))
            if dist < best_dist:
                best_dist = dist
                best = i
        return best
    # Default: luminance → 4 shades (0 = lightest)
    luma = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return 3 - min(3, int(luma / 64))


def load_tileset(
    path: str,
    tile_w: int = 8,
    tile_h: int = 8,
    palette: Optional[List[Color]] = None,
) -> List[Tile]:
    """Slice an image into a list of Tiles.

    Args:
        path:    Path to a PNG (or any pygame-supported format).
        tile_w:  Width  of each tile in pixels (default 8).
        tile_h:  Height of each tile in pixels (default 8).
        palette: Optional list of up to 4 RGB tuples used for color matching.
                 If None, the image is converted via luminance.

    Returns:
        List of Tile objects, row-major order (left→right, top→bottom).
    """
    try:
        import pygame
    except ImportError:
        raise ImportError("pygame is required for image loading")

    img = pygame.image.load(path).convert()
    img_w, img_h = img.get_size()
    tiles: List[Tile] = []

    for ty in range(img_h // tile_h):
        for tx in range(img_w // tile_w):
            pixels = []
            for py in range(tile_h):
                row = []
                for px in range(tile_w):
                    color = img.get_at((tx * tile_w + px, ty * tile_h + py))[:3]
                    row.append(_rgb_to_gb(color, palette))
                pixels.append(row)
            tiles.append(Tile(pixels))

    return tiles


def load_tile(
    path: str,
    palette: Optional[List[Color]] = None,
) -> Tile:
    """Load a single 8×8 tile from an image file."""
    tiles = load_tileset(path, 8, 8, palette)
    if not tiles:
        raise ValueError(f"No 8×8 tiles found in {path!r}")
    return tiles[0]


def tiles_from_pixels(
    pixel_grid: Sequence[Sequence[int]],
    tile_w: int = 8,
    tile_h: int = 8,
) -> List[Tile]:
    """Slice a 2-D list of color indices into Tile objects.

    Useful for defining level tilemaps inline without an image file.
    """
    h = len(pixel_grid)
    w = len(pixel_grid[0]) if h else 0
    tiles: List[Tile] = []
    for ty in range(h // tile_h):
        for tx in range(w // tile_w):
            cell = [
                [pixel_grid[ty * tile_h + py][tx * tile_w + px] for px in range(tile_w)]
                for py in range(tile_h)
            ]
            tiles.append(Tile(cell))
    return tiles


def surface_to_tile(
    surface,
    x: int = 0,
    y: int = 0,
    palette: Optional[List[Color]] = None,
) -> Tile:
    """Convert an 8×8 region of a pygame Surface into a Tile."""
    pixels = []
    for py in range(8):
        row = []
        for px in range(8):
            color = surface.get_at((x + px, y + py))[:3]
            row.append(_rgb_to_gb(color, palette))
        pixels.append(row)
    return Tile(pixels)
