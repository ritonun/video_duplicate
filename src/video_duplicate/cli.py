# cli.py

from pathlib import Path
from typing import Annotated

import typer

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
    remove_video_under_Xs,
    Progress,
    Cache,
)

app = typer.Typer()


def load_all_creators_folders(path: Path) -> list[Path]:
    creators_folders = [
        p for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")
    ]

    # Include the root folder if it contains videos.
    if any(
        file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS
        for file in path.iterdir()
    ):
        creators_folders.append(path)

    return creators_folders


def move_non_video_to_trash(paths: list[Path], trash_dir: str, simulate=False):
    total = 0
    for folder in paths:
        for file in folder.iterdir():
            total += 1
    progress = Progress(total)

    for folder in paths:
        for file in folder.iterdir():
            print(progress.get_str())
            if file.is_file() and file.suffix.lower() not in VIDEO_EXTENSIONS:
                if simulate:
                    print(f"SIMULATE - TRASHED {file}")
                else:
                    stage_file_to_trash(str(file), str(folder), trash_dir)
            progress.update()


@app.command()
def run(
    input_path: str,
    trash_dir: str,
    cache: Annotated[str, typer.Option("--cache", "-c", help="Path to cache")] = "",
    runtime: Annotated[
        int,
        typer.Option(
            "--runtime", "-r", min=1, help="Delete video under 'runtime' seconds"
        ),
    ] = 90,
    simulate: Annotated[bool, typer.Option("-s")] = False,
):
    print("Running video-duplicate...")
    print(f"Path: {input_path}")

    path = Path(input_path)
    creators_folders = load_all_creators_folders(path)

    # remove non-video
    move_non_video_to_trash(creators_folders, trash_dir, simulate=simulate)

    # remove video under 'runtime' seconds
    creators_folders = load_all_creators_folders(path)
    progress = Progress(len(creators_folders))
    for creator_path in creators_folders:
        print(
            f"Removing videos under {runtime}s from {creator_path.name} ({progress.get_str()}"
        )
        remove_video_under_Xs(
            creator_path,
            creator_path,
            trash_dir,
            runtime=float(runtime),
            simulate=simulate,
        )
        progress.update()

    # analyze all videos
    # create/get cache
    if cache == "":
        cached_file = Path.joinpath(path, ".cache.txt")
        print(f"No cache file provided. A cache file will be created at {cached_file}")
    else:
        if not Path(cache).is_file:
            cached_file = Path.joinpath(path, ".cache.txt")
            print(
                f"Cache file provided at {cache} does not exist. A cache file will be created at {cached_file}"
            )
        else:
            cached_file = Path(cache)

    cache_txt = Cache(str(cached_file))

    creators_folders = load_all_creators_folders(path)
    progress = Progress(len(creators_folders))
    for creator_path in creators_folders:
        print(f"Analyzing duplicates in folder {creator_path} {progress.get_str()}")
        print("Finding duplicates...", end="")
        duplicates = load_probable_duplicate_single(creator_path)
        print(f" Found {len(duplicates)}")
        dup_progress = Progress(len(duplicates))

        for duplicate in duplicates:
            print(f"{creator_path.name} progress: {dup_progress.get_str()}")
            v1, v2 = duplicate
            if not v1.exists() or not v2.exists():
                dup_progress.update(total_add=-1)
                continue
            dup_progress.update(current_add=1)

            if check_if_video_duplicate_quick_hash(v1, v2, size=1024 * 1024):
                # check if the first 1MB (size) has the same hash between the two videos
                r = pick_best_video(v1, v2)
                stage_file_to_trash(str(r), str(creator_path), trash_dir)
                print(f"HASHG: Moved to trash {r}")
                continue

            # compare audio between the two video
            similarity = acoustic_compare_two_videos(v1, v2)
            if isinstance(similarity, str):
                print(f"error for similarity between {v1} and {v2}: {similarity}")
                continue

            if similarity > 0.8:
                r = pick_best_video(v1, v2)
                stage_file_to_trash(str(r), str(creator_path), trash_dir)
                print(f"AUDIO: Moved to trash {r}")
                continue

            if check_if_duplicate_videos_phash(v1, v2):
                # best method but very long/computer intensive
                r = pick_best_video(v1, v2)
                stage_file_to_trash(str(r), str(creator_path), trash_dir)
                print(f"PHASH: Moved to trash {r}")

        progress.update()
