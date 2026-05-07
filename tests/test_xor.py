"""Round-trip tests for the XOR share scheme."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from visual_crypto.xor import xor_decrypt, xor_encrypt


def _random_image(mode: str, size=(48, 32), seed: int = 1) -> Image.Image:
    rng = np.random.default_rng(seed)
    if mode == "L":
        arr = rng.integers(0, 256, size=size[::-1], dtype=np.uint8)
    else:
        channels = 4 if mode == "RGBA" else 3
        arr = rng.integers(0, 256, size=(*size[::-1], channels), dtype=np.uint8)
    return Image.fromarray(arr, mode=mode)


@pytest.mark.parametrize("mode", ["L", "RGB", "RGBA"])
@pytest.mark.parametrize("n_shares", [2, 3, 5])
def test_xor_round_trip_recovers_original(mode: str, n_shares: int) -> None:
    src = _random_image(mode, seed=mode.__hash__() + n_shares)
    shares = xor_encrypt(src, n_shares=n_shares, seed=123)

    assert len(shares) == n_shares
    for share in shares:
        assert share.size == src.size
        assert share.mode == mode

    recovered = xor_decrypt(shares)
    assert np.array_equal(np.asarray(recovered), np.asarray(src))


def test_xor_single_share_is_not_the_secret() -> None:
    src = _random_image("RGB", seed=2)
    shares = xor_encrypt(src, n_shares=2, seed=999)
    assert not np.array_equal(np.asarray(shares[0]), np.asarray(src))
    assert not np.array_equal(np.asarray(shares[1]), np.asarray(src))


def test_xor_decrypt_order_independent() -> None:
    src = _random_image("RGB", seed=3)
    shares = xor_encrypt(src, n_shares=4, seed=4)
    a = np.asarray(xor_decrypt(shares))
    b = np.asarray(xor_decrypt(list(reversed(shares))))
    assert np.array_equal(a, b)


def test_xor_rejects_too_few_shares() -> None:
    with pytest.raises(ValueError):
        xor_encrypt(_random_image("L"), n_shares=1)
    with pytest.raises(ValueError):
        xor_decrypt([_random_image("L")])


def test_xor_rejects_mismatched_share_sizes() -> None:
    a = _random_image("RGB", size=(16, 16), seed=5)
    b = _random_image("RGB", size=(32, 16), seed=6)
    with pytest.raises(ValueError):
        xor_decrypt([a, b])
