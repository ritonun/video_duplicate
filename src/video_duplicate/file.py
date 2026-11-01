# src/video_duplicate/file.py

import datetime
import os
import shutil
from itertools import combinations
from pathlib import Path

from .utils import Progress, get_duration


def load_probable_duplicate(folders: list[Path], tolerance: float = 5.0):
    """Find probable duplicate videos across multiple folders."""

    videos_by_folder = [load_videos_from_folder(folder) for folder in folders]

    durations = {
        video: get_duration(video) for videos in videos_by_folder for video in videos
    }

    duplicates = []

    for videos1, videos2 in combinations(videos_by_folder, 2):
        for video1 in videos1:
            duration1 = durations[video1]

            if duration1 is None:
                continue

            for video2 in videos2:
                duration2 = durations[video2]

                if duration2 is None:
                    continue

                if abs(duration1 - duration2) <= tolerance:
                    duplicates.append([video1, video2])

    return duplicates


def load_probable_duplicate_single(
    folder: Path, tolerance: float = 5.0
) -> list[list[Path]]:
    """Find probable duplicate videos within a folder."""

    videos = load_videos_from_folder(folder)
    durations = {video: get_duration(video) for video in videos}

    return [
        [video1, video2]
        for video1, video2 in combinations(videos, 2)
        if (
            (duration1 := durations.get(video1)) is not None
            and (duration2 := durations.get(video2)) is not None
            and abs(duration1 - duration2) <= tolerance
        )
    ]


def load_videos_from_folder(path: Path) -> list[Path]:
    """From a folder load all videos"""

    videos = []
    files = list(path.iterdir())
    for file in files:
        p = Path(file)
        if p.suffix.lower() in VIDEO_EXTENSIONS:
            videos.append(file)
    return videos


VIDEO_EXTENSIONS = {
    ".3g2",
    ".3gp",
    ".asf",
    ".avi",
    ".divx",
    ".dv",
    ".f4v",
    ".flv",
    ".m1v",
    ".m2p",
    ".m2t",
    ".m2ts",
    ".m2v",
    ".m4v",
    ".mkv",
    ".mod",
    ".mov",
    ".mp2",
    ".mp4",
    ".mpe",
    ".mpeg",
    ".mpg",
    ".mts",
    ".mxf",
    ".ogm",
    ".ogv",
    ".qt",
    ".rm",
    ".rmvb",
    ".tod",
    ".ts",
    ".vob",
    ".webm",
    ".wmv",
}


def stage_file_to_trash(filepath: str, base_dir: str, trash_dir: str = ".trash") -> str:
    """
    Safely moves a rejected video file to a trash staging area,
    preserving its original relative directory structure.

    Args:
        filepath (str): Absolute or relative path to the file to discard.
        base_dir (str): Root folder being managed/scanned by the CLI tool.
        trash_dir (str): Folder where discarded files are staged (default '.trash').

    Returns:
        str: Destination path where the file was moved.
    """
    # Normalize paths to handle relative paths cleanly
    filepath = os.path.abspath(filepath)
    base_dir = os.path.abspath(base_dir)
    trash_dir = os.path.abspath(trash_dir)

    if not os.path.exists(filepath):
        print(f"[!] File not found: {filepath}")
        return ""

    # Determine the relative path from the base root folder
    # e.g., if base_dir = "/videos", filepath = "/videos/artist1/clip.mp4"
    # relative_path becomes "artist1/clip.mp4"
    try:
        relative_path = os.path.relpath(filepath, start=base_dir)
    except ValueError:
        # Fallback if filepath is on a different drive/volume
        relative_path = os.path.basename(filepath)

    # Construct full target path inside the trash directory
    target_path = os.path.join(trash_dir, relative_path)
    target_folder = os.path.dirname(target_path)

    # Ensure target directory structure exists
    os.makedirs(target_folder, exist_ok=True)

    # Handle filename collision in trash folder
    if os.path.exists(target_path):
        filename, ext = os.path.splitext(target_path)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = f"{filename}_{timestamp}{ext}"

    # Move file safely
    shutil.move(filepath, target_path)
    print(f"[Trash] Staged rejected duplicate: {relative_path} -> {target_path}")

    return target_path


def remove_video_under_Xs(
    path: Path, base_dir: Path, trash_dir, runtime=90.0, simulate=False
):
    videos = load_videos_from_folder(path)
    progress = Progress(len(videos))

    for v in videos:
        trashed = False
        duration = get_duration(v)
        if duration is None:
            print(f"Failed to read duration of {v}")
            continue
        if duration < runtime:
            if not simulate:
                stage_file_to_trash(str(path), str(base_dir), trash_dir)
                trashed = True

            print(f"SIMULATED - TRASHED {v}")
        if trashed:
            print(f"TRASHED '{v}'")

        print(f"{progress.get_str()}")
        progress.update(current_add=1)


class Cache:
    """
    Video cache.

    File format:
        video;hash;audio;phash

    Uses a dictionary indexed by video path for O(1) lookups.
    Changes are kept in memory until flush() is called.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.path.touch()

        self.videos: dict[str, dict[str, str]] = {}
        self.dirty = False

        self.load()

    def load(self) -> dict[str, dict[str, str]]:
        """Load the cache file into memory."""

        videos = {}

        with open(self.path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.rstrip("\r\n")

                if not line:
                    continue

                data = line.split(";", 3)

                if len(data) != 4:
                    print(f"Error reading cache line {line_number}: {line!r}")
                    continue

                video, hash_value, audio, phash = data

                videos[video] = {
                    "hash": hash_value,
                    "audio": audio,
                    "phash": phash,
                }

        self.videos = videos
        self.dirty = False

        return self.videos

    def save(
        self,
        video: str | Path,
        hash: str | None = None,
        audio: str | None = None,
        phash: str | None = None,
    ) -> None:
        """Update a video cache entry in memory."""

        video = str(video)

        if video not in self.videos:
            self.videos[video] = {
                "hash": "",
                "audio": "",
                "phash": "",
            }

        entry = self.videos[video]

        if hash is not None:
            entry["hash"] = hash

        if audio is not None:
            entry["audio"] = audio

        if phash is not None:
            entry["phash"] = phash

        self.dirty = True

    def find(self, video: str | Path) -> dict[str, str] | None:
        """Find a video entry in O(1)."""

        return self.videos.get(str(video))

    def get_param(
        self,
        video: str | Path,
        param: str,
    ) -> str | None:
        """Get a cached parameter."""

        entry = self.find(video)

        if entry is None:
            return None

        value = entry.get(param)

        return value if value else None

    def flush(self) -> None:
        """Write all cached entries to disk."""

        if not self.dirty:
            return

        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            f.writelines(
                f"{video};{entry['hash']};{entry['audio']};{entry['phash']}\n"
                for video, entry in self.videos.items()
            )

        # Atomic replacement to reduce the risk of a corrupted cache.
        temp_path.replace(self.path)

        self.dirty = False

    def close(self) -> None:
        """Save pending changes."""

        self.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.flush()
        return False
