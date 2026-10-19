# file.py

import datetime
import os
import shutil
from itertools import combinations
from pathlib import Path

from .utils import get_duration


def load_probable_duplicate(folders: list[Path], tolerance=2.0):
    """Find probable duplicate videos across multiple folders"""

    videos_by_folder = [load_videos_from_folder(folder) for folder in folders]
    durations = {
        video: get_duration(video) for videos in videos_by_folder for video in videos
    }

    duplicates = []

    for videos1, videos2 in combinations(videos_by_folder, 2):
        for video1 in videos1:
            duration1 = durations[video1]

            for video2 in videos2:
                duration2 = durations[video2]

                if abs(duration1 - duration2) <= tolerance:
                    duplicates.append([video1, video2])

    return duplicates


def load_videos_from_folder(path: Path):
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
