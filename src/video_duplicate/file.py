# src/video_duplicate/file.py

import datetime
import json
import os
import shutil
from itertools import combinations

from .database import Video


def load_probable_duplicate_single(
    videos: list[Video],
    tolerance: float = 5.0,
) -> list[list[Video]]:
    """Find probable duplicates within a creator."""

    return [
        [video1, video2]
        for video1, video2 in combinations(videos, 2)
        if (
            video1.runtime is not None
            and video2.runtime is not None
            and abs(video1.runtime - video2.runtime) <= tolerance
        )
    ]


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


def stage_file_to_trash(
    filepath: str, base_dir: str = None, trash_dir: str = ".trash"
) -> str:
    """
    Safely moves a rejected video file to a local trash staging area.
    Works on Debian/headless Linux without desktop environment trash dependencies.
    """
    # Expand ~ and make absolute
    filepath = os.path.abspath(os.path.expanduser(filepath))

    if base_dir is not None:
        base_dir = None

    if not os.path.exists(filepath):
        print(f"[!] File not found: {filepath}")
        return ""

    if os.path.isdir(filepath):
        print(f"[!] Error: '{filepath}' is a directory, not a file.")
        return ""

    filename = os.path.basename(filepath)

    # Properly expand ~/ paths for trash_dir
    trash_dir = os.path.abspath(os.path.expanduser(trash_dir))
    target_path = os.path.join(trash_dir, filename)
    meta_path = target_path + ".meta.json"

    # Ensure target trash directory exists
    os.makedirs(trash_dir, exist_ok=True)

    # Handle filename collision gracefully if multiple folders have files with the same name
    if os.path.exists(target_path):
        name, ext = os.path.splitext(filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target_path = os.path.join(trash_dir, f"{name}_{timestamp}{ext}")
        meta_path = target_path + ".meta.json"

    # Save original absolute path in metadata for effortless restoration
    metadata = {
        "original_path": filepath,
        "trashed_at": datetime.datetime.now().isoformat(),
    }

    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    # Move file to trash
    shutil.move(filepath, target_path)

    return target_path


def restore_file_from_trash(trashed_filepath: str) -> str:
    """
    Restores a file from the local trash back to its exact original location
    using its saved metadata sidecar file.
    """
    trashed_filepath = os.path.abspath(os.path.expanduser(trashed_filepath))
    meta_path = trashed_filepath + ".meta.json"

    if not os.path.exists(trashed_filepath):
        print(f"[!] Trashed file not found: {trashed_filepath}")
        return ""

    if not os.path.exists(meta_path):
        print(
            f"[!] Metadata missing for {trashed_filepath}. Cannot automatically restore."
        )
        return ""

    # Read original path from metadata
    with open(meta_path, "r") as f:
        metadata = json.load(f)

    original_path = metadata["original_path"]

    # Ensure original parent directory exists
    os.makedirs(os.path.dirname(original_path), exist_ok=True)

    # Handle collision if something already exists at the original path
    restore_target = original_path
    if os.path.exists(restore_target):
        filename, ext = os.path.splitext(restore_target)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        restore_target = f"{filename}_restored_{timestamp}{ext}"
        print(f"[!] Original path occupied. Restoring to: {restore_target}")

    # Move file back
    shutil.move(trashed_filepath, restore_target)

    # Clean up metadata file
    os.remove(meta_path)

    print(f"[Restore] Successfully restored to: {restore_target}")
    return restore_target
