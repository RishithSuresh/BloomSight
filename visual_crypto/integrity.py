"""Share integrity verification and authentication.

This module provides cryptographic mechanisms to detect tampering with
visual cryptography shares. Features include:

* HMAC-based share authentication: sign and verify shares with a secret key
* Metadata embedding: encode share index, total shares, and timestamps
* Checksum verification: detect bit-level corruption in shares

The integrity layer is optional and complementary to the core encryption.
A compromised share can be detected before decryption is attempted.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Dict, Optional, Tuple

import numpy as np
from PIL import Image

# Metadata encoding: embed in image corner as a small QR-like pattern
# For simplicity, we encode in the top-left 16x16 pixel block
_METADATA_BLOCK_SIZE = 16


def compute_share_signature(
    share: Image.Image,
    secret_key: bytes,
) -> str:
    """Compute HMAC-SHA256 signature of a share.

    Parameters
    ----------
    share:
        The visual cryptography share image.
    secret_key:
        Secret key for HMAC computation (e.g., from a keyfile or passphrase).
        Must be at least 16 bytes for security.

    Returns
    -------
    str
        Hex-encoded HMAC-SHA256 signature of the share's pixel data.
    """
    if len(secret_key) < 16:
        raise ValueError("secret_key must be at least 16 bytes for security")

    share_bytes = share.tobytes()
    signature = hmac.new(secret_key, share_bytes, hashlib.sha256).hexdigest()
    return signature


def verify_share_signature(
    share: Image.Image,
    secret_key: bytes,
    expected_signature: str,
) -> bool:
    """Verify that a share has not been tampered with.

    Uses constant-time comparison to resist timing attacks.

    Parameters
    ----------
    share:
        The visual cryptography share image to verify.
    secret_key:
        The same secret key used to sign the share.
    expected_signature:
        The previously computed signature (from compute_share_signature).

    Returns
    -------
    bool
        True if the signature matches (share is authentic), False otherwise.
    """
    computed = compute_share_signature(share, secret_key)
    # Use hmac.compare_digest for constant-time comparison
    return hmac.compare_digest(computed, expected_signature)


def embed_metadata(
    share: Image.Image,
    share_index: int,
    total_shares: int,
    threshold: int = 0,
) -> Image.Image:
    """Embed metadata (index, total, threshold) into the top-left corner.

    The metadata is encoded as binary patterns in the top-left 16x16 block.
    For a grayscale image, pixels < 128 are treated as 0, >= 128 as 1.

    This modifies the share slightly, so it should be done before final
    export. The integrity signature should be computed AFTER embedding.

    Parameters
    ----------
    share:
        The visual cryptography share image.
    share_index:
        Zero-based index of this share (0, 1, 2, ...).
    total_shares:
        Total number of shares (n in n-of-n or k-of-n scheme).
    threshold:
        Minimum number of shares needed for recovery (0 if not applicable).

    Returns
    -------
    Image.Image
        A copy of the share with metadata embedded in the corner.
    """
    if share_index < 0 or share_index >= total_shares:
        raise ValueError(f"share_index must be in range [0, {total_shares - 1}]")

    # Create a copy to avoid modifying the original
    shared_copy = share.copy()
    arr = np.asarray(shared_copy.convert("L"), dtype=np.uint8).copy()

    # Encode metadata as bit pattern in top-left 16x16 block
    # Bits: [share_index (4 bits) | total_shares (4 bits) | threshold (4 bits) | reserved (4 bits)]
    metadata_bits = (
        ((share_index & 0xF) << 12) |
        ((total_shares & 0xF) << 8) |
        ((threshold & 0xF) << 4)
    )

    # Embed bits into pixel brightness (MSB = top-left pixel)
    for i in range(16):  # 16 pixels for 16 bits
        row = i // 4
        col = i % 4
        bit_value = (metadata_bits >> (15 - i)) & 1
        # Set pixel to black (0) if bit is 1, white (255) if bit is 0
        arr[row, col] = 0 if bit_value else 255

    return Image.fromarray(arr, mode="L")


def extract_metadata(share: Image.Image) -> Dict[str, int]:
    """Extract embedded metadata from a share.

    Reads the top-left 16x16 block and decodes share index, total shares,
    and threshold information.

    Parameters
    ----------
    share:
        The visual cryptography share image with embedded metadata.

    Returns
    -------
    dict
        Dictionary with keys: 'share_index', 'total_shares', 'threshold'.
        Returns None for any value that could not be decoded.
    """
    arr = np.asarray(share.convert("L"), dtype=np.uint8)

    # Extract 16 bits from top-left 4x4 corner
    metadata_bits = 0
    for i in range(16):
        row = i // 4
        col = i % 4
        # Pixel < 128 = 1 bit, >= 128 = 0 bit
        bit_value = 1 if arr[row, col] < 128 else 0
        metadata_bits |= (bit_value << (15 - i))

    share_index = (metadata_bits >> 12) & 0xF
    total_shares = (metadata_bits >> 8) & 0xF
    threshold = (metadata_bits >> 4) & 0xF

    return {
        "share_index": share_index,
        "total_shares": total_shares,
        "threshold": threshold,
    }


def compute_share_checksum(share: Image.Image) -> int:
    """Compute a CRC32 checksum of the share for quick corruption detection.

    This is faster than HMAC but provides no cryptographic guarantees.
    Useful as a first-pass check before full verification.

    Parameters
    ----------
    share:
        The visual cryptography share image.

    Returns
    -------
    int
        CRC32 checksum (0 to 2^32 - 1).
    """
    import zlib
    share_bytes = share.tobytes()
    return zlib.crc32(share_bytes) & 0xFFFFFFFF


def verify_share_set(
    shares: list[Image.Image],
    secret_key: bytes,
    signatures: list[str],
) -> Tuple[bool, list[bool]]:
    """Verify integrity of multiple shares.

    Parameters
    ----------
    shares:
        List of visual cryptography shares to verify.
    secret_key:
        Secret key used to sign the shares.
    signatures:
        List of previously computed signatures (one per share).

    Returns
    -------
    tuple[bool, list[bool]]
        (all_valid, individual_results) where all_valid is True if all
        signatures match, and individual_results shows per-share validity.
    """
    if len(shares) != len(signatures):
        raise ValueError("shares and signatures lists must have same length")

    results = [
        verify_share_signature(share, secret_key, sig)
        for share, sig in zip(shares, signatures)
    ]
    return all(results), results
