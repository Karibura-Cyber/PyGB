"""TMX tilemap loader — import Tiled maps into PyGB using pytmx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .game import GameBoy
    from .tilemap import TileMap

Color = Tuple[int, int, int]


@dataclass
class TmxObject:
    """A single object from a Tiled object layer."""

    name: str
    type: str
    x: float
    y: float
    width: float
    height: float
    properties: dict = field(default_factory=dict)


@dataclass
class TmxResult:
    """Data returned by load_tmx.

    Attributes:
        tile_size:    Tile width/height in pixels (from the TMX file).
        map_cols:     Map width in tiles.
        map_rows:     Map height in tiles.
        world_w:      World width in pixels (map_cols * tile_size).
        world_h:      World height in pixels (map_rows * tile_size).
        layers:       All tile layers keyed by layer name.
        layer_order:  Layer names in their original TMX order (bottom → top).
        objects:      Object groups keyed by group name.
        properties:   Map-level custom properties dict.
        surfaces:     Raw pygame.Surfaces keyed by VRAM index for full-colour
                      rendering.  Use these instead of the palette-quantised
                      Tile objects when you want the original tileset colours.
    """

    tile_size: int
    map_cols: int
    map_rows: int
    world_w: int
    world_h: int
    layers: Dict[str, "TileMap"]
    layer_order: List[str]
    objects: Dict[str, List[TmxObject]]
    properties: dict
    surfaces: Dict[int, object] = field(default_factory=dict)


def load_tmx(
    gb: "GameBoy",
    path: str,
    bg_layer: Union[int, str] = 0,
    palette: Optional[List[Color]] = None,
) -> TmxResult:
    """Load a Tiled .tmx file into PyGB.

    Unique tiles from the tileset are loaded into ``gb.graphics`` VRAM and
    ``gb.graphics.bg`` is replaced with the tile layer selected by *bg_layer*.
    All tile layers are accessible in the returned ``TmxResult.layers`` dict.

    The tile size reported by the TMX file is also stored in ``gb.tile_size``
    so that the render loop uses the correct grid spacing automatically.

    Args:
        gb:       The GameBoy instance to load tiles into.
        path:     Path to the ``.tmx`` file.
        bg_layer: Index (int) or name (str) of the tile layer to assign to
                  ``gb.graphics.bg``.  Defaults to the first tile layer (0).
        palette:  Optional list of up to 4 RGB tuples for colour quantisation.
                  If None, luminance quantisation is used.

    Returns:
        :class:`TmxResult` containing dimensions, all layers, object groups,
        and map-level custom properties.

    Raises:
        ImportError: if ``pytmx`` is not installed.
        FileNotFoundError: if *path* does not exist.
        ValueError: if the TMX file contains no tile layers.

    Example::

        from pygb import GameBoy, load_tmx, CollisionMap
        import pygb.color as color

        gb = GameBoy(title="Tiled Demo", scale=3, palette=color.DMG)

        @gb.on_start
        def init():
            result = load_tmx(gb, "level1.tmx")
            # tile_size is set automatically on gb
            cmap = CollisionMap(result.map_cols, result.map_rows,
                                tile_size=result.tile_size)
            # mark tiles from an object layer as solid, etc.

        gb.run()
    """
    try:
        import pytmx
    except ImportError:
        raise ImportError(
            "pytmx is required for TMX loading: pip install pytmx"
        )

    import pygame
    from .tilemap import TileMap
    from .tile import Tile
    from .assets import _rgb_to_gb

    tiled_map = pytmx.load_pygame(path)
    tile_w: int = tiled_map.tilewidth
    tile_h: int = tiled_map.tileheight

    tile_layers = [
        l for l in tiled_map.layers
        if isinstance(l, pytmx.TiledTileLayer)
    ]
    object_groups = [
        l for l in tiled_map.layers
        if isinstance(l, pytmx.TiledObjectGroup)
    ]

    if not tile_layers:
        raise ValueError(f"No tile layers found in {path!r}")

    # Reserve VRAM index 0 as the "empty cell" sentinel so real tiles start at 1.
    # TileMap cells default to 0; checking `idx in surfaces` then correctly
    # skips empty cells without conflicting with a real tile at index 0.
    gb.graphics.add_tile(Tile.solid(0))

    # gid → VRAM index; avoids adding duplicate tile surfaces
    gid_to_vram: Dict[int, int] = {}
    # vram index → original pygame.Surface (full colour, no palette quantisation)
    raw_surfaces: Dict[int, "pygame.Surface"] = {}

    def _surface_to_tile(surf: "pygame.Surface") -> Tile:
        s = surf.convert()
        pixels = [
            [_rgb_to_gb(s.get_at((px, py))[:3], palette) for px in range(tile_w)]
            for py in range(tile_h)
        ]
        return Tile(pixels)

    def _vram_index(gid: int) -> Optional[int]:
        if gid == 0:
            return None
        if gid in gid_to_vram:
            return gid_to_vram[gid]
        surf = tiled_map.get_tile_image_by_gid(gid)
        if surf is None:
            return None
        idx = gb.graphics.add_tile(_surface_to_tile(surf))
        gid_to_vram[gid] = idx
        raw_surfaces[idx] = surf.convert_alpha()
        return idx

    # Build a TileMap for every tile layer
    result_layers: Dict[str, TileMap] = {}
    layer_order: List[str] = []
    bg_tilemap: Optional[TileMap] = None

    for layer_idx, layer in enumerate(tile_layers):
        tilemap = TileMap(width=tiled_map.width, height=tiled_map.height)
        for x, y, gid in layer:
            idx = _vram_index(gid)
            if idx is not None:
                tilemap.set(x, y, idx)
        result_layers[layer.name] = tilemap
        layer_order.append(layer.name)

        is_bg = (
            layer_idx == bg_layer
            if isinstance(bg_layer, int)
            else layer.name == bg_layer
        )
        if is_bg:
            bg_tilemap = tilemap

    if bg_tilemap is None:
        bg_tilemap = next(iter(result_layers.values()))

    gb.graphics.bg = bg_tilemap
    gb.tile_size = tile_w

    # Collect object groups
    result_objects: Dict[str, List[TmxObject]] = {}
    for group in object_groups:
        objs = [
            TmxObject(
                name=obj.name or "",
                type=getattr(obj, "type", "") or "",
                x=obj.x,
                y=obj.y,
                width=float(obj.width or 0),
                height=float(obj.height or 0),
                properties=dict(obj.properties) if obj.properties else {},
            )
            for obj in group
        ]
        result_objects[group.name] = objs

    return TmxResult(
        tile_size=tile_w,
        map_cols=tiled_map.width,
        map_rows=tiled_map.height,
        world_w=tiled_map.width * tile_w,
        world_h=tiled_map.height * tile_h,
        layers=result_layers,
        layer_order=layer_order,
        objects=result_objects,
        properties=dict(tiled_map.properties) if tiled_map.properties else {},
        surfaces=raw_surfaces,
    )
