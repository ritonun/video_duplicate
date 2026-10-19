import shutil
import time
from pathlib import Path

from video_duplicate import (
    acoustic_compare_two_videos,
    check_if_duplicate_videos_phash,
    check_if_video_duplicate_quick_hash,
    load_probable_duplicate,
    load_videos_from_folder,
    VIDEO_EXTENSIONS,
    pick_best_video,
    stage_file_to_trash,
    get_duration,
    load_probable_duplicate_single,
)

TRASH = Path("/home/jerry/optiplex/.video_trash")


class Progress:
    def __init__(self, total, current=1):
        self.total = total
        self.current = current

    def update(self, current_add=0, total_add=0) -> None:
        self.current += current_add
        self.total += total_add

    def get_percent(self) -> float:
        percent = self.current / self.total * 100
        return round(percent, 1)

    def get_str(self) -> str:
        return f"{self.current}/{self.total} {self.get_percent()}%"


def move_to_trash(video: Path) -> None:
    TRASH.mkdir(exist_ok=True)
    shutil.move(str(video), str(TRASH / video.name))


def load_all_creators_folders(path: Path) -> list[Path]:
    return [
        p
        for p in path.iterdir()
        if p.is_dir() and p.name != ".cache" and p.name != ".video_trash"
    ]


def remove_video_under_90s(path: Path):
    videos = load_videos_from_folder(path)
    progress = Progress(len(videos))

    for v in videos:
        trashed = False
        duration = get_duration(v)
        if duration is None:
            print(f"Failed to read duration of {v}")
            continue
        if duration < 90.0:
            move_to_trash(v)
            trashed = True
        if trashed:
            print(f"TRASHED '{v}'")

        print(f"{progress.get_str()}")
        progress.update(current_add=1)


if __name__ == "__main__":
    # load all creators
    path = Path("/home/jerry/optiplex/")

    """
    # remove video under 1min30s
    creators_folders = load_all_creators_folders(path)
    total_progress = Progress(len(creators_folders))

    for creators_path in creators_folders:
        print(f"REMOVING VIDEO UNDER 90s - PROGRESS {total_progress.get_str()}")
        print(creators_path.name)
        remove_video_under_90s(creators_path)
        total_progress.update(current_add=1)
    """

    # remove duplicate
    creators_folders = load_all_creators_folders(path)
    total_progress = Progress(len(creators_folders))

    for creators_path in creators_folders:
        print(f"CREATOR {creators_path.name} {total_progress.get_str()}")
        duplicates = load_probable_duplicate_single(creators_path)
        progress = Progress(len(duplicates))

        for duplicate in duplicates:
            print(f"{creators_path.name} progress: {progress.get_str()}")
            v1, v2 = duplicate
            if not v1.exists() or not v2.exists():
                progress.update(total_add=-1)
                continue
            progress.update(current_add=1)

            if check_if_video_duplicate_quick_hash(v1, v2, size=1024 * 1024):
                # check if the first 1MB (size) has the same hash between the two videos
                r = pick_best_video(v1, v2)
                move_to_trash(r)
                print(f"HASHG: Moved to trash {r}")
                continue

            # compare audio between the two video
            similarity = acoustic_compare_two_videos(v1, v2)
            if isinstance(similarity, str):
                print(f"error for similarity between {v1} and {v2}: {similarity}")
                continue

            if similarity > 0.8:
                r = pick_best_video(v1, v2)
                move_to_trash(r)
                print(f"AUDIO: Moved to trash {r}")
                continue

            if check_if_duplicate_videos_phash(v1, v2):
                # best method but very long/computer intensive
                r = pick_best_video(v1, v2)
                move_to_trash(r)
                print(f"PHASH: Moved to trash {r}")

        total_progress.update(current_add=1)
