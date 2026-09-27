import hashlib
import json
import os
import subprocess
import tempfile

from videohash import VideoHash

from .audio import compare_vids
from .hashing import check_if_duplicate_videos


def load_videos(path: str):
    videos = []
    files = os.listdir(path)
    for file in files:
        videos.append(os.path.join(path, file))
    return videos


def get_duration(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return float(result.stdout.strip())


def load_probable_duplicate(path1, path2, tolerance=2.0):

    duplicates = []

    videos1 = load_videos(path1)
    videos2 = load_videos(path2)

    for video1 in videos1:
        duration1 = get_duration(video1)

        for video2 in videos2:
            duration2 = get_duration(video2)

            if abs(duration1 - duration2) <= tolerance:
                duplicates.append([video1, video2])

    return duplicates


def hash_first_1mb(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(1024 * 1024))
    return h.digest()


def write_to_csv(va, vb, line):
    full_line = va.split("/")[-1] + ";" + vb.split("/")[-1] + ";" + line
    if not full_line.endswith("\n"):
        full_line += "\n"
    with open("data/result.csv", "a") as f:
        f.write(full_line)


def main() -> None:

    header = "v1; v2; hash 1MB; phash; audio same; audio likely;"
    with open("data/result.csv", "w") as f:
        f.write(header + "\n")

    print("Searching duplicates...")

    duplicates = load_probable_duplicate("data/1/", "data/2/")
    print(f"Found {len(duplicates)} probable duplicates")
    for d in duplicates:
        line = ""

        va, vb = d[0], d[1]
        print(f"Result of:\n{va}\n{vb}")
        ha = hash_first_1mb(va)
        hb = hash_first_1mb(vb)
        same = ha == hb
        print(f"SAME (HASH 1MB): {same}")
        line += f"{same};"

        tolerance = 4
        same = check_if_duplicate_videos(va, vb, tolerance=tolerance)
        print(f"HASHING (tol={tolerance}): {same}")
        line += f"{same};"

        similarity = compare_vids(va, vb)
        same = False
        likely = False
        if similarity > 0.9:
            same = True
            likely = True
        if not same and similarity > 0.8:
            likely = True
        print(f"AUDIO: {same} (likely={likely})")
        print("--- ---\n")
        line += f"{same};{likely};"
        write_to_csv(va, vb, line)
