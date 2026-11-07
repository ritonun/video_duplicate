# src/video_duplicate/cli.py

from pathlib import Path
from typing import Annotated

import typer
from tqdm import tqdm

from video_duplicate import (
    VIDEO_EXTENSIONS,
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
    DB,
    Video,
    Status,
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


def scan_and_sync_videos(path: Path, db: DB) -> list[Path]:
    """Find creator folders containing videos and register videos in the DB."""

    tqdm.write("Scanning creators folders...")
    creators_folders = [
        folder
        for folder in path.iterdir()
        if folder.is_dir()
        and not folder.name.startswith(".")
        and any(
            file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS
            for file in folder.iterdir()
            if not file.name.startswith(".")
        )
    ]

    # Include the root folder if it directly contains videos.
    if any(
        file.is_file()
        and file.suffix.lower() in VIDEO_EXTENSIONS
        and not file.name.startswith(".")
        for file in path.iterdir()
    ):
        creators_folders.append(path)

    # Register every discovered video in the database.
    tqdm.write("Registering all videos found into db...")

    videos = [
        file
        for folder in creators_folders
        for file in folder.iterdir()
        if file.is_file()
        and not file.name.startswith(".")
        and file.suffix.lower() in VIDEO_EXTENSIONS
    ]

    new_video_found = 0

    for i, file in enumerate(videos):
        if db.get_video(file) is None:
            runtime = get_duration(file)

            if runtime is None:
                tqdm.write(f"Could not get runtime for {file}")

            db.get_or_create_video(file, runtime=runtime)
            new_video_found += 1
            tqdm.write(f"{new_video_found} {i}/{len(videos)}", end="\r")

    if new_video_found == 0:
        tqdm.write("No new video found.")
    else:
        tqdm.write(f"Found {new_video_found} new video.")

    # Remove records for files that no longer exist.
    removed = db.remove_missing_files()
    if removed:
        tqdm.write(f"Removed {removed} missing videos from database")

    return creators_folders


def move_non_video_to_trash(paths: list[Path], trash_dir: str, simulate=False):
    total = 0
    for folder in paths:
        for file in folder.iterdir():
            total += 1

    for folder in tqdm(paths, desc="Folders progress", unit="f", leave=False):
        for file in folder.iterdir():
            if file.name.startswith("."):
                continue
            if file.is_file() and file.suffix.lower() not in VIDEO_EXTENSIONS:
                if simulate:
                    tqdm.write(f"SIMULATE - TRASHED {file}")
                else:
                    stage_file_to_trash(str(file), trash_dir)


def qhash(v1: Video, v2: Video, db: DB, creator_path: str, trash_dir: str) -> bool:
    size = 1024 * 1024

    video1 = db.get_or_create_video(v1.path)
    video2 = db.get_or_create_video(v2.path)

    if video1.qhash is None:
        h1 = hash_first_mb_comparison(v1, size=size)
        db.update_video(v1.path, qhash=str(h1))
    else:
        h1 = video1.qhash

    if video2.qhash is None:
        h2 = hash_first_mb_comparison(v2, size=size)
        db.update_video(v2.path, qhash=str(h2))
    else:
        h2 = video2.qhash

    if h1 == h2:
        # check if the first 1MB (size) has the same hash between the two videos
        worst_video = pick_worst_video(v1, v2)
        stage_file_to_trash(str(worst_video), Path(creator_path).name, trash_dir)
        tqdm.write(f"HASHG: Moved to trash {worst_video}")
        return True
    return False


def audio(
    v1: Video,
    v2: Video,
    db: DB,
    creator_path: str,
    trash_dir: str,
) -> bool:
    fingerprint_length = 60

    video1 = db.get_or_create_video(v1.path)
    video2 = db.get_or_create_video(v2.path)

    # Get or calculate the first video's fingerprint.
    if video1.audio is not None and video1.audio_duration is not None:
        audio1 = (video1.audio_duration, video1.audio)
    else:
        audio1 = acoustic_fingerprint(
            v1.path,
            fingerprint_length=fingerprint_length,
        )

        if audio1 is None:
            tqdm.write(f"Error getting audio fingerprint of {v1.name}")
            return False

        duration, fingerprint = audio1

        db.update_video(
            v1.path,
            audio=fingerprint,
            audio_duration=duration,
        )

    # Get or calculate the second video's fingerprint.
    if video2.audio is not None and video2.audio_duration is not None:
        audio2 = (video2.audio_duration, video2.audio)
    else:
        audio2 = acoustic_fingerprint(
            v2.path,
            fingerprint_length=fingerprint_length,
        )

        if audio2 is None:
            tqdm.write(f"Error getting audio fingerprint of {v2.name}")
            return False

        duration, fingerprint = audio2

        db.update_video(
            v2.path,
            audio=fingerprint,
            audio_duration=duration,
        )

    similarity = compare_acoustic_fingerprints(audio1, audio2)

    if isinstance(similarity, str):
        tqdm.write(
            f"Error comparing audio between {v1.name} and {v2.name}: {similarity}"
        )
        return False

    if similarity > 0.8:
        worst_video = pick_worst_video(v1, v2)

        stage_file_to_trash(
            str(worst_video),
            Path(creator_path).name,
            trash_dir,
        )

        tqdm.write(f"AUDIO: Moved to trash {worst_video}")
        return True

    return False


def phash(
    v1: Video,
    v2: Video,
    db: DB,
    creator_path: str,
    trash_dir: str,
) -> bool:
    temp_dir = trash_dir + "/.temp"
    frame_interval = 2
    tolerance = 4

    video1 = db.get_or_create_video(v1.path)
    video2 = db.get_or_create_video(v2.path)

    if video1.phash is None:
        p1 = get_video_phash(
            v1.path,
            temp_dir,
            frame_interval=frame_interval,
        )

        if p1 is None:
            tqdm.write(f"Failed to get phash of video {v1.name}")
            return False

        p1 = str(p1)
        db.update_video(v1.path, phash=p1)
    else:
        p1 = video1.phash

    if video2.phash is None:
        p2 = get_video_phash(
            v2.path,
            temp_dir,
            frame_interval=frame_interval,
        )

        if p2 is None:
            tqdm.write(f"Failed to get phash of video {v2.name}")
            return False

        p2 = str(p2)
        db.update_video(v2.path, phash=p2)
    else:
        p2 = video2.phash

    if are_videos_duplicates(p1, p2, tolerance=tolerance):
        worst_video = pick_worst_video(v1.path, v2.path)

        stage_file_to_trash(
            str(worst_video),
            Path(creator_path).name,
            trash_dir,
        )

        tqdm.write(f"PHASH: Moved to trash {worst_video}")
        return True

    return False


def remove_short_videos(db: DB, runtime: float, trash_dir: str, simulate: bool = False):
    videos = db.get_videos_under_runtime(runtime)

    for video in tqdm(
        videos, desc=f"Removing videos under {runtime}s", unit="v", leave=False
    ):
        path = Path(video.path)
        if not path.exists():
            tqdm.write(f"DB sync problem: path {path} does not exist.")
            continue

        if simulate:
            tqdm.write(f"SIMULATE - TRASHED {path}")
            continue

        stage_file_to_trash(str(path), video.creator, trash_dir)
        tqdm.write(f"TRASHED {path}")

        db.update_video(path, status=Status.DELETED)


@app.command()
def run(
    input_path: str,
    trash_dir: str,
    database: Annotated[
        str,
        typer.Option("--database", "-d", help="Path to SQLite database"),
    ] = "",
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

    if database == "":
        database_file = path / ".video-duplicate.db"
        print(
            f"No database file provided. A database will be created at {database_file}"
        )
    else:
        database_file = Path(database)

    with DB(database_file) as db:
        # Scan folders and synchronize videos with the database.
        creators_folders = scan_and_sync_videos(path, db)

        # Remove non-video files.
        if remove_non_videos:
            move_non_video_to_trash(
                creators_folders,
                trash_dir,
                simulate=simulate,
            )

        # Remove videos under the requested runtime.
        if not skip_runtime:
            remove_short_videos(db, runtime, trash_dir, simulate=simulate)

        # Analyze duplicates.
        if dup_qhash or dup_audio or dup_phash:
            for creator_path in tqdm(
                creators_folders, desc="creators progress", unit="c", leave=True
            ):
                duplicates = load_probable_duplicate_single(
                    db.get_videos_by_creator(str(creator_path))
                )
                tqdm.write(f" Found {len(duplicates)} duplicates")

                for video1, video2 in tqdm(
                    duplicates,
                    desc=f"{creator_path.name} progress",
                    unit="d",
                    leave=False,
                ):
                    if not Path(video1.path).exists() or not Path(video2.path).exists():
                        continue

                    if dup_qhash and qhash(
                        video1, video2, db, str(creator_path), trash_dir
                    ):
                        continue

                    if dup_audio and audio(
                        video1, video2, db, str(creator_path), trash_dir
                    ):
                        continue

                    if dup_phash and phash(
                        video1, video2, db, str(creator_path), trash_dir
                    ):
                        continue
