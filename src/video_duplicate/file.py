# file.py

import os
from itertools import combinations
from pathlib import Path

from .utils import get_duration


def load_probable_duplicate(folders: list[str], tolerance=2.0):
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


def load_videos_from_folder(path: str):
    """From a folder load all videos"""

    videos = []
    files = os.listdir(path)
    for file in files:
        p = Path(file)
        if p.suffix.lower() in VIDEO_EXTENSIONS:
            videos.append(os.path.join(path, file))
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
