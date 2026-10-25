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
)

app = typer.Typer()


def load_all_creators_folders(path: Path) -> list[Path]:
    return [p for p in path.iterdir() if p.is_dir() and not p.name.startswith(".")]


@app.command()
def run(
    input_path: str,
    trash_dir: str,
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
    if any(
        file.is_file() and file.suffix.lower() in VIDEO_EXTENSIONS
        for file in path.iterdir()
    ):
        creators_folders.append(path)

    # remove video under 'runtime' seconds
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
