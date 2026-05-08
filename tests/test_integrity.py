"""Tests for share integrity verification module."""

import unittest

from PIL import Image

from visual_crypto import integrity, xor


class TestShareSignature(unittest.TestCase):
    """Test HMAC-based share authentication."""

    def setUp(self):
        """Create a test image and shares."""
        # Create a simple test image
        self.test_image = Image.new("L", (32, 32), color=128)
        self.secret_key = b"test_secret_key_123456"  # 22 bytes

    def test_compute_signature(self):
        """Test signature computation returns consistent hex string."""
        shares = xor.xor_encrypt(self.test_image, n_shares=2)
        sig = integrity.compute_share_signature(shares[0], self.secret_key)
        # Signature should be a 64-char hex string (SHA256 = 256 bits = 64 hex chars)
        self.assertEqual(len(sig), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in sig))

    def test_signature_deterministic(self):
        """Same image + same key = same signature."""
        shares = xor.xor_encrypt(self.test_image, n_shares=2, seed=42)
        sig1 = integrity.compute_share_signature(shares[0], self.secret_key)
        sig2 = integrity.compute_share_signature(shares[0], self.secret_key)
        self.assertEqual(sig1, sig2)

    def test_signature_changes_with_key(self):
        """Different keys produce different signatures."""
        shares = xor.xor_encrypt(self.test_image, n_shares=2, seed=42)
        sig1 = integrity.compute_share_signature(shares[0], self.secret_key)
        sig2 = integrity.compute_share_signature(shares[0], b"different_key_12345678")
        self.assertNotEqual(sig1, sig2)

    def test_short_key_rejected(self):
        """Secret key must be at least 16 bytes."""
        shares = xor.xor_encrypt(self.test_image, n_shares=2)
        with self.assertRaises(ValueError):
            integrity.compute_share_signature(shares[0], b"short")

    def test_verify_valid_signature(self):
        """Verify should return True for correct signature."""
        shares = xor.xor_encrypt(self.test_image, n_shares=2)
        sig = integrity.compute_share_signature(shares[0], self.secret_key)
        result = integrity.verify_share_signature(shares[0], self.secret_key, sig)
        self.assertTrue(result)

    def test_verify_invalid_signature(self):
        """Verify should return False for incorrect signature."""
        shares = xor.xor_encrypt(self.test_image, n_shares=2)
        sig = integrity.compute_share_signature(shares[0], self.secret_key)
        result = integrity.verify_share_signature(shares[1], self.secret_key, sig)
        self.assertFalse(result)

    def test_verify_detects_tampering(self):
        """Verify detects if share was modified after signing."""
        shares = xor.xor_encrypt(self.test_image, n_shares=2)
        sig = integrity.compute_share_signature(shares[0], self.secret_key)

        # Tamper with the share
        tampered = shares[0].copy()
        arr = tampered.tobytes()
        # Flip a byte
        modified_bytes = bytearray(arr)
        modified_bytes[0] ^= 1
        tampered = Image.frombytes(shares[0].mode, shares[0].size, bytes(modified_bytes))

        result = integrity.verify_share_signature(tampered, self.secret_key, sig)
        self.assertFalse(result)


class TestMetadata(unittest.TestCase):
    """Test metadata embedding and extraction."""

    def setUp(self):
        """Create test image and shares."""
        self.test_image = Image.new("L", (64, 64), color=200)
        self.shares = xor.xor_encrypt(self.test_image, n_shares=3, seed=42)

    def test_embed_metadata(self):
        """Test embedding metadata does not crash."""
        result = integrity.embed_metadata(self.shares[0], 0, 3, threshold=1)
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, self.shares[0].size)
        self.assertEqual(result.mode, "L")

    def test_extract_metadata(self):
        """Test round-trip: embed then extract."""
        share_with_meta = integrity.embed_metadata(self.shares[0], 1, 3, threshold=2)
        meta = integrity.extract_metadata(share_with_meta)

        self.assertEqual(meta["share_index"], 1)
        self.assertEqual(meta["total_shares"], 3)
        self.assertEqual(meta["threshold"], 2)

    def test_metadata_multiple_shares(self):
        """Test metadata for multiple shares."""
        for i in range(3):
            share = integrity.embed_metadata(self.shares[i], i, 3)
            meta = integrity.extract_metadata(share)
            self.assertEqual(meta["share_index"], i)
            self.assertEqual(meta["total_shares"], 3)

    def test_invalid_share_index(self):
        """Invalid share index should raise error."""
        with self.assertRaises(ValueError):
            integrity.embed_metadata(self.shares[0], 5, 3)


class TestChecksum(unittest.TestCase):
    """Test checksum-based corruption detection."""

    def setUp(self):
        """Create test image."""
        self.test_image = Image.new("L", (32, 32), color=128)
        self.shares = xor.xor_encrypt(self.test_image, n_shares=2, seed=42)

    def test_checksum_consistent(self):
        """Checksum should be deterministic."""
        cs1 = integrity.compute_share_checksum(self.shares[0])
        cs2 = integrity.compute_share_checksum(self.shares[0])
        self.assertEqual(cs1, cs2)

    def test_checksum_differs_per_share(self):
        """Different shares should have different checksums."""
        cs1 = integrity.compute_share_checksum(self.shares[0])
        cs2 = integrity.compute_share_checksum(self.shares[1])
        self.assertNotEqual(cs1, cs2)

    def test_checksum_is_integer(self):
        """Checksum should be 32-bit unsigned integer."""
        cs = integrity.compute_share_checksum(self.shares[0])
        self.assertIsInstance(cs, int)
        self.assertGreaterEqual(cs, 0)
        self.assertLess(cs, 2**32)


class TestShareSetVerification(unittest.TestCase):
    """Test batch verification of multiple shares."""

    def setUp(self):
        """Create test shares."""
        test_image = Image.new("L", (32, 32), color=128)
        self.shares = xor.xor_encrypt(test_image, n_shares=3, seed=42)
        self.secret_key = b"multi_share_verification_key"

    def test_verify_all_valid(self):
        """Verify returns True when all shares are authentic."""
        sigs = [integrity.compute_share_signature(s, self.secret_key) for s in self.shares]
        all_valid, individual = integrity.verify_share_set(self.shares, self.secret_key, sigs)
        self.assertTrue(all_valid)
        self.assertTrue(all(individual))

    def test_verify_one_tampered(self):
        """Verify detects if one share was tampered with."""
        sigs = [integrity.compute_share_signature(s, self.secret_key) for s in self.shares]

        # Tamper with second share
        tampered_shares = self.shares.copy()
        arr = bytearray(self.shares[1].tobytes())
        arr[10] ^= 0xFF  # Flip bits
        tampered_shares[1] = Image.frombytes(self.shares[1].mode, self.shares[1].size, bytes(arr))

        all_valid, individual = integrity.verify_share_set(tampered_shares, self.secret_key, sigs)
        self.assertFalse(all_valid)
        self.assertTrue(individual[0])
        self.assertFalse(individual[1])
        self.assertTrue(individual[2])

    def test_verify_mismatched_lengths(self):
        """Should raise error if shares and signatures lists differ in length."""
        sigs = [integrity.compute_share_signature(s, self.secret_key) for s in self.shares[:2]]
        with self.assertRaises(ValueError):
            integrity.verify_share_set(self.shares, self.secret_key, sigs)


if __name__ == "__main__":
    unittest.main()
