# src/video_duplicate/hashing.py
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from PIL import Image

# Compatibility for libraries still using Image.ANTIALIAS
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # type: ignore


from videohash import VideoHash


def hash_first_mb_comparison(path, size=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(size))
    return h.digest()


def get_video_phash(filepath: Path | str, frame_interval=2):
    """
    Safely generates a perceptual hash for a video file.
    Returns the hexadecimal hash string, or None if it fails.
    """
    temp_dir = tempfile.TemporaryDirectory()
    try:
        # The library creates temporary directories for frame extraction.
        # It usually cleans them up, but we wrap in a try-except to be safe.
        vh = VideoHash(
            str(filepath),
            storage_path=temp_dir.name,
            frame_interval=frame_interval,
        )
        return vh.hash_hex
    except Exception as e:
        print(f"[!] Error hashing {filepath}: {e}")
        return None
    finally:
        temp_dir.cleanup()


def are_videos_duplicates(hash_hex_1, hash_hex_2, tolerance=4):
    """
    Compares two hexadecimal hashes.
    Returns True if the hamming distance is <= tolerance.
    """
    if not hash_hex_1 or not hash_hex_2:
        return False

    # Convert hex strings to integers
    int1 = int(hash_hex_1, 16)
    int2 = int(hash_hex_2, 16)

    # XOR the two integers, then count the '1' bits to get the Hamming distance
    hamming_distance = bin(int1 ^ int2).count("1")

    return hamming_distance <= tolerance


def check_if_duplicate_videos_phash(
    path1: Path | str, path2: Path | str, tolerance=4, frame_interval=2
):
    """
    Takes two video paths, generates their perceptual hashes,
    and returns True if they are duplicates within the given tolerance.
    """
    # 1. Generate hashes for both videos
    hash1 = get_video_phash(path1, frame_interval=frame_interval)
    hash2 = get_video_phash(path2, frame_interval=frame_interval)

    # 2. Compare the hex strings using the existing function
    return are_videos_duplicates(hash1, hash2, tolerance)


def check_if_video_duplicate_quick_hash(
    path1: Path | str, path2: Path | str, size=1024 * 1024
):
    ha = hash_first_mb_comparison(path1, size=size)
    hb = hash_first_mb_comparison(path2, size=size)
    return ha == hb, ha, hb
