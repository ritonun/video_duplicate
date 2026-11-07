# src/video_duplicate/hashing.py
import hashlib
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


def get_video_phash(filepath: Path | str, temp_dir: str, frame_interval=2):
    """
    Safely generates a perceptual hash for a video file.
    Returns the hexadecimal hash string, or None if it fails.
    """
    vh = None
    try:
        vh = VideoHash(
            str(filepath),
            frame_interval=frame_interval,
        )
        return vh.hash_hex
    except Exception as e:
        print(f"[!] Error hashing {filepath}: {e}")
        return None
    finally:
        if vh is not None:
            try:
                vh.delete_storage_path()
            except Exception as e:
                print(f"[!] Warning: Could not clean up temp files for {filepath}: {e}")


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
