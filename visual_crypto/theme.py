"""BloomSight nature-themed brand palette and share styling.

The cryptographic algorithms in this package operate on raw pixels.
This module is purely cosmetic: it lets each share be exported as a
two-tone image painted in the BloomSight nature palette so the output
looks like organic art rather than RGB noise, while still being
losslessly convertible back to the binary share for decryption.
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from PIL import Image

RGB = Tuple[int, int, int]

# --- Brand palette (BloomSight) ------------------------------------------------
DEEP_FOREST_GREEN: RGB = (0x1B, 0x5E, 0x20)
FRESH_LEAF_GREEN: RGB = (0x4C, 0xAF, 0x50)
EARTH_BROWN: RGB = (0x6D, 0x4C, 0x41)
SKY_BLUE: RGB = (0x4F, 0xC3, 0xF7)
SOFT_YELLOW: RGB = (0xFB, 0xC0, 0x2D)
ALERT_RED: RGB = (0xE5, 0x39, 0x35)
LIGHT_BG: RGB = (0xF1, 0xF8, 0xE9)
DARK_BG: RGB = (0x0D, 0x1B, 0x12)

# Default foreground/background pairing for each share index.
SHARE_PALETTES: Tuple[Tuple[RGB, RGB], ...] = (
    (DEEP_FOREST_GREEN, LIGHT_BG),   # share 1 - forest on light
    (EARTH_BROWN, LIGHT_BG),         # share 2 - earth on light
    (SKY_BLUE, DARK_BG),             # share 3 - sky on night
    (SOFT_YELLOW, DARK_BG),          # share 4 - sun on night
    (FRESH_LEAF_GREEN, LIGHT_BG),    # share 5 - leaf on light
)


def palette_for(share_index: int) -> Tuple[RGB, RGB]:
    """Return ``(foreground, background)`` for the given share index."""
    return SHARE_PALETTES[share_index % len(SHARE_PALETTES)]


def apply_nature_tint(
    binary_share: Image.Image,
    fg: RGB = DEEP_FOREST_GREEN,
    bg: RGB = LIGHT_BG,
) -> Image.Image:
    """Recolor a 1-bit (or grayscale) share into a two-tone RGB image.

    Dark pixels of the share become ``fg``, light pixels become ``bg``.
    The mapping is deterministic and inverted by :func:`from_nature_tint`.
    """
    gray = np.asarray(binary_share.convert("L"))
    is_ink = gray < 128
    rgb = np.empty((*gray.shape, 3), dtype=np.uint8)
    rgb[is_ink] = fg
    rgb[~is_ink] = bg
    return Image.fromarray(rgb, mode="RGB")


def from_nature_tint(themed_image: Image.Image) -> Image.Image:
    """Recover a binary share from a themed RGB image via luminance.

    The returned image is in mode ``L`` (0 = ink, 255 = background) to
    avoid Pillow's default dithering when converting to mode ``1``.
    """
    gray = np.asarray(themed_image.convert("L"))
    binary = np.where(gray < 128, 0, 255).astype(np.uint8)
    return Image.fromarray(binary, mode="L")


def banner(title: str = "BloomSight Visual Cryptography") -> str:
    """Return a small ANSI-coloured banner for CLI output."""
    g = "\x1b[38;2;76;175;80m"   # leaf green
    d = "\x1b[38;2;27;94;32m"    # deep forest
    b = "\x1b[38;2;109;76;65m"   # earth brown
    r = "\x1b[0m"
    leaf = g + "\u2698" + r  # flower-like glyph; falls back gracefully
    line = "\u2500" * (len(title) + 4)
    bar = d + line + r
    return bar + "\n" + leaf + "  " + b + title + r + "\n" + bar
