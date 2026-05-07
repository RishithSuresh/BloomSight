"""Tests for the BloomSight nature-themed share styling."""

from __future__ import annotations

import numpy as np
from PIL import Image

from visual_crypto import theme
from visual_crypto.naor_shamir import naor_shamir_encrypt


def _checker(size=(8, 8)) -> Image.Image:
    arr = np.zeros(size, dtype=np.uint8)
    arr[::2, ::2] = 255
    arr[1::2, 1::2] = 255
    return Image.fromarray(arr, mode="L").convert("1")


def test_palette_has_expected_brand_colors() -> None:
    assert theme.DEEP_FOREST_GREEN == (0x1B, 0x5E, 0x20)
    assert theme.FRESH_LEAF_GREEN == (0x4C, 0xAF, 0x50)
    assert theme.EARTH_BROWN == (0x6D, 0x4C, 0x41)
    assert theme.SKY_BLUE == (0x4F, 0xC3, 0xF7)


def test_palette_for_cycles() -> None:
    n = len(theme.SHARE_PALETTES)
    assert theme.palette_for(0) == theme.palette_for(n)
    assert theme.palette_for(1) == theme.palette_for(n + 1)


def test_apply_nature_tint_uses_only_two_colors() -> None:
    share = _checker()
    tinted = theme.apply_nature_tint(share, fg=theme.DEEP_FOREST_GREEN,
                                     bg=theme.LIGHT_BG)
    pixels = {tuple(p) for p in np.asarray(tinted).reshape(-1, 3).tolist()}
    assert pixels == {theme.DEEP_FOREST_GREEN, theme.LIGHT_BG}


def test_tint_round_trip_preserves_share() -> None:
    _, share = naor_shamir_encrypt(_checker(size=(16, 16)), seed=0)
    tinted = theme.apply_nature_tint(share, fg=theme.EARTH_BROWN,
                                     bg=theme.LIGHT_BG)
    recovered = theme.from_nature_tint(tinted)

    a = np.asarray(share.convert("L")) < 128
    b = np.asarray(recovered.convert("L")) < 128
    assert np.array_equal(a, b)


def test_banner_contains_title() -> None:
    text = theme.banner("Hello Forest")
    assert "Hello Forest" in text
