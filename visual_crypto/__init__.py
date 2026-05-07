"""BloomSight Visual Cryptography.

A nature-themed visual cryptography toolkit. Splits an image into
multiple shares that, on their own, look like noise (or themed art),
and only reveal the original when combined.

Two algorithms are provided:

* ``xor``         - Exact-recovery n-of-n cryptographic split that works
                    on any RGB/RGBA/grayscale image.
* ``naor_shamir`` - Classic 2-of-2 visual cryptography for binary
                    images, recoverable by stacking the shares.
"""

from .xor import xor_encrypt, xor_decrypt
from .naor_shamir import naor_shamir_encrypt, naor_shamir_decrypt
from . import theme

__all__ = [
    "xor_encrypt",
    "xor_decrypt",
    "naor_shamir_encrypt",
    "naor_shamir_decrypt",
    "theme",
]
