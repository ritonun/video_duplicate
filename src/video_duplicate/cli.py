# src/video_duplicate/cli.py

from pathlib import Path
from typing import Annotated
import base64
import json

import typer

from video_duplicate import (
    VIDEO_EXTENSIONS,
    Cache,
    Progress,
    acoustic_compare_two_videos,
    acoustic_fingerprint,
    are_videos_duplicates,
    check_if_duplicate_videos_phash,
    check_if_video_duplicate_quick_hash,
    compare_acoustic_fingerprints,
    get_duration,
    get_video_phash,
    hash_first_mb_comparison,
    load_probable_duplicate,
    load_probable_duplicate_single,
    load_videos_from_folder,
    pick_best_video,
    remove_video_under_Xs,
    stage_file_to_trash,
    pick_worst_video,
)

type Fingerprint = tuple[float, bytes]
app = typer.Typer()


def fingerprint_to_cache(fingerprint: Fingerprint) -> str:
    """Convert a fingerprint into a text-safe string."""

    duration, fingerprint_bytes = fingerprint

    data = {
        "duration": duration,
        "fingerprint": base64.b64encode(fingerprint_bytes).decode("ascii"),
    }

    return json.dumps(data)


def fingerprint_from_cache(value: str) -> Fingerprint | None:
    """Restore the exact original fingerprint from the cache."""

    try:
        data = json.loads(value)

        duration = float(data["duration"])
        fingerprint_bytes = base64.b64decode(data["fingerprint"], validate=True)

        return duration, fingerprint_bytes

    except Exception:
        return None


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
            if file.name.startswith("."):
                continue
            if file.is_file() and file.suffix.lower() not in VIDEO_EXTENSIONS:
                if simulate:
                    print(f"SIMULATE - TRASHED {file}")
                else:
                    stage_file_to_trash(str(file), trash_dir)
            progress.update()


def qhash(v1: Path, v2: Path, cache: Cache, creator_path: str, trash_dir: str) -> bool:
    size = 1024 * 1024

    v1_cache = cache.find(v1)
    if v1_cache is None or v1_cache["hash"] == "":
        h1 = hash_first_mb_comparison(v1, size=size)
        cache.save(v1, hash=str(h1))
    else:
        h1 = v1_cache["hash"]

    v2_cache = cache.find(v2)
    if v2_cache is None or v2_cache["hash"] == "":
        h2 = hash_first_mb_comparison(v2, size=size)
        cache.save(v2, hash=str(h2))
    else:
        h2 = v2_cache["hash"]

    if h1 == h2:
        # check if the first 1MB (size) has the same hash between the two videos
        r = pick_worst_video(v1, v2)
        stage_file_to_trash(str(r), Path(creator_path).name, trash_dir)
        print(f"HASHG: Moved to trash {r}")
        return True
    return False


def audio(v1: Path, v2: Path, cache: Cache, creator_path: str, trash_dir: str) -> bool:

    fingerprint_length = 60

    # video 1
    cached_audio1 = cache.get_param(v1, "audio")

    if cached_audio1 is not None:
        audio1 = fingerprint_from_cache(cached_audio1)
    else:
        audio1 = None

    if audio1 is None:
        audio1 = acoustic_fingerprint(
            v1,
            fingerprint_length=fingerprint_length,
        )

        if audio1 is None:
            print(f"Error getting audio fingerprint of {v1}")
            return False

        cache.save(
            v1,
            audio=fingerprint_to_cache(audio1),
        )

    # video 2
    cached_audio2 = cache.get_param(v2, "audio")

    if cached_audio2 is not None:
        audio2 = fingerprint_from_cache(cached_audio2)
    else:
        audio2 = None

    if audio2 is None:
        audio2 = acoustic_fingerprint(
            v2,
            fingerprint_length=fingerprint_length,
        )

        if audio2 is None:
            print(f"Error getting audio fingerprint of {v2}")
            return False

        cache.save(
            v2,
            audio=fingerprint_to_cache(audio2),
        )

    # compare
    similarity = compare_acoustic_fingerprints(
        audio1,
        audio2,
    )

    if isinstance(similarity, str):
        print(f"Error comparing audio between {v1} and {v2}: {similarity}")
        return False

    print(f"Audio similarity: {similarity:.4f}")

    if similarity > 0.8:
        worst_video = pick_worst_video(v1, v2)

        stage_file_to_trash(
            str(worst_video),
            Path(creator_path).name,
            trash_dir,
        )

        print(f"AUDIO: Moved to trash {worst_video}")
        return True

    return False


def phash(v1: Path, v2: Path, cache: Cache, creator_path: str, trash_dir: str) -> bool:
    temp_dir = trash_dir + "/.temp"
    frame_interval = 2
    tolerance = 4
    p1 = cache.get_param(v1, "phash")
    if p1 is None:
        p1 = get_video_phash(v1, temp_dir, frame_interval=frame_interval)
        if p1 is None:
            print(f"Failed to get phash of video {v1}")
            return False
        cache.save(v1, phash=str(p1))
    p2 = cache.get_param(v2, "phash")
    if p2 is None:
        p2 = get_video_phash(v2, temp_dir, frame_interval=frame_interval)
        if p2 is None:
            print(f"Failed to get phash of video {v2}")
            return False
        cache.save(v2, phash=str(p2))

    if are_videos_duplicates(p1, p2, tolerance=tolerance):
        r = pick_worst_video(v1, v2)
        stage_file_to_trash(str(r), Path(creator_path).name, trash_dir)
        print(f"PHASH: Moved to trash {r}")
        return True
    return False


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
    skip_runtime: Annotated[bool, typer.Option("--skip-runtime")] = False,
    remove_non_videos: Annotated[bool, typer.Option("-n")] = False,
    dup_qhash: Annotated[bool, typer.Option("-q")] = False,
    dup_audio: Annotated[bool, typer.Option("-a")] = False,
    dup_phash: Annotated[bool, typer.Option("-p")] = False,
):
    print("Running video-duplicate...")
    print(f"Path: {input_path}")

    path = Path(input_path)
    creators_folders = load_all_creators_folders(path)

    # remove non-video
    if remove_non_videos:
        move_non_video_to_trash(creators_folders, trash_dir, simulate=simulate)

    # remove video under 'runtime' seconds
    if not skip_runtime:
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

    if dup_qhash or dup_audio or dup_phash:
        # analyze all videos
        # create/get cache
        if cache == "":
            cached_file = Path.joinpath(path, ".cache.txt")
            print(
                f"No cache file provided. A cache file will be created at {cached_file}"
            )
        else:
            cached_file = Path(cache)
        cache_txt = Cache(cached_file)

        creators_folders = load_all_creators_folders(path)
        progress = Progress(len(creators_folders))
        for creator_path in creators_folders:
            print(f"Analyzing duplicates in folder {creator_path} {progress.get_str()}")
            print("Finding duplicates...", end="")
            duplicates = load_probable_duplicate_single(creator_path)
            print(f" Found {len(duplicates)}")
            dup_progress = Progress(len(duplicates))

            for duplicate in duplicates:
                # reload cache
                cache_txt = Cache(cached_file)

                print(f"{creator_path.name} progress: {dup_progress.get_str()}")

                v1, v2 = duplicate
                if not v1.exists() or not v2.exists():
                    dup_progress.update(total_add=-1)
                    continue
                dup_progress.update(current_add=1)

                if dup_qhash:
                    if qhash(v1, v2, cache_txt, str(creator_path), trash_dir):
                        continue
                if dup_audio:
                    if audio(v1, v2, cache_txt, str(creator_path), trash_dir):
                        continue
                if dup_phash:
                    if phash(v1, v2, cache_txt, str(creator_path), trash_dir):
                        continue

                cache_txt.flush()

            cache_txt.flush()
            progress.update()

        cache_txt.remove_missing_files()
