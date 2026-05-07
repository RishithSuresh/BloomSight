"""Naor-Shamir 2-of-2 visual cryptography.

This is the classical visual secret-sharing scheme from Naor & Shamir
(1994). The original is a *binary* image. Each pixel is expanded into a
2x2 sub-block in two shares such that:

* For a **white** pixel both shares receive an identical sub-block.
  When stacked (logical OR of the ink) the result has 2 black sub-pixels
  out of 4 - mid-grey.
* For a **black** pixel the second share receives the *complement* of
  the first share's sub-block. When stacked the result is fully black
  (4 of 4 sub-pixels).

Either share alone is a uniformly-random pattern of 50% black sub-pixels
and reveals nothing about the secret. Combine them by stacking
(transparency / minimum-darkness) and the original silhouette appears.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from PIL import Image

# Six 2x2 sub-pixel patterns containing exactly two black cells.
# 1 represents an inked sub-pixel, 0 represents a clear one.
_PATTERNS = np.array(
    [
        [[1, 0], [0, 1]],   # diagonal
        [[0, 1], [1, 0]],   # anti-diagonal
        [[1, 1], [0, 0]],   # top
        [[0, 0], [1, 1]],   # bottom
        [[1, 0], [1, 0]],   # left
        [[0, 1], [0, 1]],   # right
    ],
    dtype=np.uint8,
)


def _to_binary_mask(image: Image.Image) -> np.ndarray:
    """Return an array where 1 marks black (ink) pixels of the secret.

    A plain luminance threshold is used (no dithering) so the binarisation
    is reproducible and a tinted-then-restored share decodes identically.
    """
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    return (gray < 128).astype(np.uint8)


def _ink_to_image(ink: np.ndarray) -> Image.Image:
    """Convert a 0/1 ink mask to an 8-bit Pillow image (0=ink, 255=clear).

    The result is kept in mode ``L`` rather than ``1`` so that subsequent
    PNG round-trips and theme tinting stay strictly bit-exact.
    """
    pixels = ((1 - ink) * 255).astype(np.uint8)
    return Image.fromarray(pixels, mode="L")


def naor_shamir_encrypt(
    image: Image.Image,
    seed: Optional[int] = None,
) -> Tuple[Image.Image, Image.Image]:
    """Split a binary image into two visually-cryptographic shares.

    The output shares are each twice as wide and twice as tall as the
    input because every pixel is expanded into a 2x2 sub-block.
    """
    secret = _to_binary_mask(image)
    h, w = secret.shape
    rng = np.random.default_rng(seed)

    idx = rng.integers(0, len(_PATTERNS), size=(h, w))
    block_a = _PATTERNS[idx]                              # (h, w, 2, 2)
    is_black = secret[..., None, None] == 1
    block_b = np.where(is_black, 1 - block_a, block_a)    # (h, w, 2, 2)

    # Reshape (h, w, 2, 2) -> (2h, 2w) by interleaving block rows/cols.
    share_a = block_a.transpose(0, 2, 1, 3).reshape(h * 2, w * 2)
    share_b = block_b.transpose(0, 2, 1, 3).reshape(h * 2, w * 2)

    return _ink_to_image(share_a), _ink_to_image(share_b)


def naor_shamir_decrypt(
    share_a: Image.Image,
    share_b: Image.Image,
) -> Image.Image:
    """Stack two shares to reveal the secret image.

    Stacking is modelled as the per-pixel minimum on a grayscale view:
    a sub-pixel is dark in the result if it is dark in either share.
    """
    if share_a.size != share_b.size:
        raise ValueError("Shares must be the same size to be stacked")
    a = np.asarray(share_a.convert("L"), dtype=np.uint8)
    b = np.asarray(share_b.convert("L"), dtype=np.uint8)
    stacked = np.minimum(a, b)
    return Image.fromarray(stacked, mode="L")


def downsample_revealed(stacked: Image.Image) -> Image.Image:
    """Optionally collapse a stacked share back to original resolution.

    Each 2x2 sub-block is averaged; the result is then thresholded so
    fully-black blocks become black ink and half-black blocks become
    white. This is purely cosmetic - the visible reveal already works
    without it, this just removes the 2x scaling.
    """
    arr = np.asarray(stacked.convert("L"), dtype=np.uint8)
    if arr.shape[0] % 2 or arr.shape[1] % 2:
        raise ValueError("Stacked image dimensions must be even to downsample")
    h2, w2 = arr.shape[0] // 2, arr.shape[1] // 2
    blocks = arr.reshape(h2, 2, w2, 2).mean(axis=(1, 3))
    binary = np.where(blocks < 64, 0, 255).astype(np.uint8)
    return Image.fromarray(binary, mode="L").convert("1")
