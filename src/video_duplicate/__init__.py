# src/video_duplicate/__init__.py

from .audio import (
    acoustic_fingerprint,
    compare_acoustic_fingerprints,
)
from .file import (
    VIDEO_EXTENSIONS,
    stage_file_to_trash,
    load_probable_duplicate_single,
)
from .hashing import (
    hash_first_mb_comparison,
    are_videos_duplicates,
    get_video_phash,
)
from .quality import pick_best_video, pick_worst_video
from .utils import get_duration
from .database import DB, Status, Video
