# audio .py
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import acoustid

type Fingerprint = tuple[float, bytes]


@dataclass(frozen=True)
class AcousticConfig:
    """Configuration for acoustic video comparison"""

    fingerprint_length: int = 60  # how much audio to fingerprint in each videos
    strong_match_threshold: float = 0.90
    likely_match_threshold: float = 0.8


@dataclass(frozen=True)
class AcousticResult:
    """Result of acoustic comparison between two videos"""

    similarity: float  # between 0.0 and 1.0, 1.0 meaning it is the same videos
    confidence: str
    same: bool
    reason: str | None = None


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
    *,
    config: AcousticConfig | None = None,
) -> AcousticResult:
    """Compare two locally generated Chromaprint fingerprints."""

    config = config or AcousticConfig()

    if fingerprint1 is None:
        return AcousticResult(
            similarity=0.0,
            confidence="unknown",
            same=False,
            reason="Could not fingerprint video 1",
        )

    if fingerprint2 is None:
        return AcousticResult(
            similarity=0.0,
            confidence="unknown",
            same=False,
            reason="Could not fingerprint video 2.",
        )

    try:
        similarity = acoustid.compare_fingerprints(
            fingerprint1,
            fingerprint2,
        )
    except Exception as exc:
        return AcousticResult(
            similarity=0.0,
            confidence="unknown",
            same=False,
            reason=f"Fingerprint comparison failed: {exc}",
        )

    if similarity >= config.strong_match_threshold:
        return AcousticResult(
            similarity=similarity,
            confidence="same",
            same=True,
        )
    if similarity >= config.likely_match_threshold:
        return AcousticResult(
            similarity=similarity,
            confidence="likely",
            same=False,
        )

    return AcousticResult(
        similarity=similarity,
        confidence="different",
        same=False,
    )


def acoustic_compare_two_videos(
    path1: Path, path2: Path, *, config: AcousticConfig | None = None
) -> AcousticResult:
    """
    Fingerprint two videos and compare their audio.
    """

    config = config or AcousticConfig()

    fingerprint1 = acoustic_fingerprint(path1, config.fingerprint_length)
    fingerprint2 = acoustic_fingerprint(path2, config.fingerprint_length)

    return compare_acoustic_fingerprints(fingerprint1, fingerprint2, config=config)
