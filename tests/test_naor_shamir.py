"""Tests for the 2-of-2 Naor-Shamir visual cryptography scheme."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from visual_crypto.naor_shamir import (
    downsample_revealed,
    naor_shamir_decrypt,
    naor_shamir_encrypt,
)


def _make_secret(size=(40, 20)) -> Image.Image:
    img = Image.new("1", size, color=1)  # white
    draw = ImageDraw.Draw(img)
    # Paint a black rectangle in the middle.
    draw.rectangle([8, 4, size[0] - 9, size[1] - 5], fill=0)
    return img


def test_shares_are_double_size() -> None:
    secret = _make_secret()
    s1, s2 = naor_shamir_encrypt(secret, seed=0)
    assert s1.size == (secret.size[0] * 2, secret.size[1] * 2)
    assert s2.size == s1.size


def test_each_share_is_roughly_50_percent_black() -> None:
    secret = _make_secret(size=(64, 64))
    s1, s2 = naor_shamir_encrypt(secret, seed=1)
    for share in (s1, s2):
        arr = np.asarray(share.convert("L"))
        ratio = (arr < 128).mean()
        assert 0.45 < ratio < 0.55, f"share black ratio {ratio} out of band"


def test_stacking_reveals_secret_silhouette() -> None:
    secret = _make_secret(size=(40, 20))
    s1, s2 = naor_shamir_encrypt(secret, seed=42)
    revealed = downsample_revealed(naor_shamir_decrypt(s1, s2))

    secret_arr = np.asarray(secret.convert("L"))
    revealed_arr = np.asarray(revealed.convert("L"))

    # Pixels that are black in the secret must be black in the reveal.
    secret_black = secret_arr < 128
    revealed_black = revealed_arr < 128
    assert np.all(revealed_black[secret_black])

    # White areas of the secret must remain white after downsampling.
    assert not np.any(revealed_black[~secret_black])


def test_single_share_does_not_reveal_secret() -> None:
    secret = _make_secret(size=(64, 64))
    s1, _ = naor_shamir_encrypt(secret, seed=7)

    # The downsampled view of a single share should look like noise,
    # not like the secret rectangle.
    solo = downsample_revealed(s1)
    secret_arr = np.asarray(secret.convert("L")) < 128
    solo_arr = np.asarray(solo.convert("L")) < 128

    matches = (secret_arr == solo_arr).mean()
    # A perfect reveal would be ~1.0; pure noise is ~0.5. Require it to
    # be far from a clean reconstruction.
    assert matches < 0.85


def test_seed_is_deterministic() -> None:
    secret = _make_secret()
    a1, a2 = naor_shamir_encrypt(secret, seed=2024)
    b1, b2 = naor_shamir_encrypt(secret, seed=2024)
    assert np.array_equal(np.asarray(a1), np.asarray(b1))
    assert np.array_equal(np.asarray(a2), np.asarray(b2))
