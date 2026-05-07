"""XOR-based n-of-n visual cryptography.

This is the *exact-recovery* family of share schemes. Given an image
``I`` and ``n`` shares, ``n - 1`` shares are filled with cryptographically
indistinguishable random pixels and the final share is computed so that
the bitwise XOR of all shares reproduces ``I`` exactly:

    I  ==  S_1 XOR S_2 XOR ... XOR S_n

Any single share, on its own, is statistically indistinguishable from
random noise (a one-time-pad style guarantee for the n=2 case). Every
share carries the same shape and pixel mode as the input image, so the
scheme works for grayscale, RGB and RGBA pictures.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import numpy as np
from PIL import Image

_SUPPORTED_MODES = ("L", "RGB", "RGBA")


def _as_array(image: Image.Image) -> np.ndarray:
    if image.mode not in _SUPPORTED_MODES:
        image = image.convert("RGB")
    return np.asarray(image, dtype=np.uint8)


def xor_encrypt(
    image: Image.Image,
    n_shares: int = 2,
    seed: Optional[int] = None,
) -> List[Image.Image]:
    """Split ``image`` into ``n_shares`` XOR shares.

    Parameters
    ----------
    image:
        Source image. ``L``, ``RGB`` and ``RGBA`` modes are supported
        directly; anything else is converted to ``RGB`` first.
    n_shares:
        Number of shares to produce. Must be at least 2.
    seed:
        Optional integer seed for the random number generator. Use this
        only for reproducible tests; in production leave it unset so a
        fresh OS-seeded PRNG is used.

    Returns
    -------
    list[Image.Image]
        ``n_shares`` Pillow images of identical size and mode.
    """
    if n_shares < 2:
        raise ValueError("n_shares must be >= 2")

    arr = _as_array(image)
    mode = "RGB" if image.mode not in _SUPPORTED_MODES else image.mode
    rng = np.random.default_rng(seed)

    accumulator = np.zeros_like(arr)
    shares: List[np.ndarray] = []
    for _ in range(n_shares - 1):
        share = rng.integers(0, 256, size=arr.shape, dtype=np.uint8)
        shares.append(share)
        accumulator = np.bitwise_xor(accumulator, share)

    final = np.bitwise_xor(arr, accumulator)
    shares.append(final)

    return [Image.fromarray(s, mode=mode) for s in shares]


def xor_decrypt(shares: Sequence[Image.Image]) -> Image.Image:
    """Combine XOR shares back into the original image.

    Order does not matter; XOR is commutative and associative. All
    shares must have the same size and pixel mode.
    """
    if len(shares) < 2:
        raise ValueError("Need at least 2 shares to decrypt")

    first = shares[0]
    mode = first.mode if first.mode in _SUPPORTED_MODES else "RGB"
    accum = _as_array(first).copy()
    for s in shares[1:]:
        if s.size != first.size:
            raise ValueError("All shares must have the same size")
        accum = np.bitwise_xor(accum, _as_array(s))
    return Image.fromarray(accum, mode=mode)
