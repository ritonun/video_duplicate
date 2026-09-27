# hashing.py
import hashlib

from PIL import Image

# Compatibility for libraries still using Image.ANTIALIAS
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # type: ignore


from videohash import VideoHash


def hash_first_1mb(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(1024 * 1024))
    return h.digest()


def get_video_phash(filepath):
    """
    Safely generates a perceptual hash for a video file.
    Returns the hexadecimal hash string, or None if it fails.
    """
    try:
        # The library creates temporary directories for frame extraction.
        # It usually cleans them up, but we wrap in a try-except to be safe.
        vh = VideoHash(filepath, frame_interval=1 / 10)
        return vh.hash_hex
    except Exception as e:
        print(f"[!] Error hashing {filepath}: {e}")
        return None


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


def check_if_duplicate_videos(path1, path2, tolerance=4):
    """
    Takes two video paths, generates their perceptual hashes,
    and returns True if they are duplicates within the given tolerance.
    """
    # 1. Generate hashes for both videos
    hash1 = get_video_phash(path1)
    hash2 = get_video_phash(path2)

    # 2. Compare the hex strings using the existing function
    return are_videos_duplicates(hash1, hash2, tolerance)
