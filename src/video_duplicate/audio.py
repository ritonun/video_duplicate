# src/video_duplicate/audio .py
from functools import lru_cache
from pathlib import Path

import acoustid

type Fingerprint = tuple[float, bytes]


@lru_cache(maxsize=1024)
def acoustic_fingerprint(
    path: Path | str, fingerprint_length: int = 60
) -> Fingerprint | None:
    """
    Generate a Chromaprint fingerprint locally.

    Returns: (duration, fingerprint) || None if fingerprinting failed
    """

    try:
        duration, fingerprint = acoustid.fingerprint_file(
            str(path),
            maxlength=fingerprint_length,
            force_fpcalc=True,
        )
    except Exception:
        return None

    if fingerprint is None:
        return None

    return float(duration), fingerprint


def compare_acoustic_fingerprints(
    fingerprint1: Fingerprint | None,
    fingerprint2: Fingerprint | None,
) -> float | str:
    """Compare two locally generated Chromaprint fingerprints."""

    if fingerprint1 is None:
        return "Could not fingerprint video 1"

    if fingerprint2 is None:
        return "Could not fingerprint video 2"

    try:
        similarity = acoustid.compare_fingerprints(
            fingerprint1,
            fingerprint2,
        )
    except Exception as exc:
        return f"[Error] Fingerprint comparison failed: {exc}"

    return float(similarity)


def acoustic_compare_two_videos(
    path1: Path, path2: Path, fingerprint_length: int = 60
) -> float | str:
    """
    Fingerprint two videos and compare their audio.
    """

    fingerprint1 = acoustic_fingerprint(path1, fingerprint_length=fingerprint_length)
    fingerprint2 = acoustic_fingerprint(path2, fingerprint_length=fingerprint_length)

    return compare_acoustic_fingerprints(fingerprint1, fingerprint2)
