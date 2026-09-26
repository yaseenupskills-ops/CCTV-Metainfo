"""Perceptual image hashing for frame analysis."""

import cv2
import numpy as np

_HASH_SIZE = 32
_HASH_BLOCK = 8


def perceptual_hash(gray: np.ndarray) -> str:
    """DCT-based perceptual hash (pHash) of a grayscale frame.

    Resize to 32x32, take the top-left 8x8 block of the DCT, and encode
    each coefficient against the block median as a 64-bit value.
    """
    resized = cv2.resize(gray, (_HASH_SIZE, _HASH_SIZE), interpolation=cv2.INTER_AREA)
    resized = (resized.astype(np.float32) - 128.0) / 128.0
    dct = cv2.dct(resized)
    block: np.ndarray = dct[:_HASH_BLOCK, :_HASH_BLOCK]
    bits = block > np.median(block)
    value = 0
    for bit in bits.reshape(-1):
        value = (value << 1) | int(bit)
    return f"{value:016x}"


def phash_distance(hash_a: str, hash_b: str) -> float:
    """Normalized Hamming distance between two 64-bit pHash hex strings (0-1)."""
    if len(hash_a) != 16 or len(hash_b) != 16:
        raise ValueError("pHash strings must be 16 hex characters")
    a = int(hash_a, 16)
    b = int(hash_b, 16)
    differing = bin(a ^ b).count("1")
    return differing / 64.0
