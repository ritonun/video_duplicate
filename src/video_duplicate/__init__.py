# __init__.py

from .audio import (
    acoustic_compare_two_videos,
    acoustic_fingerprint,
    compare_acoustic_fingerprints,
)
from .file import (
    load_probable_duplicate,
    load_videos_from_folder,
    VIDEO_EXTENSIONS,
    stage_file_to_trash,
    load_probable_duplicate_single,
    remove_video_under_Xs,
    Cache,
)
from .hashing import (
    check_if_duplicate_videos_phash,
    check_if_video_duplicate_quick_hash,
    hash_first_mb_comparison,
    are_videos_duplicates,
    get_video_phash,
)
from .quality import pick_best_video, pick_worst_video
from .utils import get_duration, Progress
