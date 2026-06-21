"""Game Boy color palettes.

The original DMG has 4 shades rendered as green-tinted grays.
Palette indices 0–3 map to: lightest → darkest.
"""

# Classic DMG green palette
DMG = [
    (224, 248, 208),  # 0 — lightest
    (136, 192, 112),  # 1 — light
    (52,  104,  86),  # 2 — dark
    (8,    24,  32),  # 3 — darkest
]

# Grayscale palette
GRAY = [
    (255, 255, 255),
    (170, 170, 170),
    (85,  85,  85),
    (0,   0,   0),
]

# Game Boy Pocket (lighter, cooler tones)
POCKET = [
    (200, 200, 168),
    (144, 144, 120),
    (88,  88,  72),
    (0,   0,   0),
]

# Game Boy Color "high contrast" style
GBC = [
    (255, 255, 255),
    (126, 207,  97),
    (36,  130,  60),
    (0,   38,   18),
]

DEFAULT = DMG
