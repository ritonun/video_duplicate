# __init__.py

from .audio import acoustic_compare_two_videos
from .file import load_probable_duplicate, load_videos_from_folder, stage_file_to_trash
from .hashing import (
    check_if_duplicate_videos_phash,
    check_if_video_duplicate_quick_hash,
)
from .quality import pick_best_video
