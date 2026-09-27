from functools import lru_cache

import acoustid

# How much audio to fingerprint from each video.
# fpcalc defaults to 120 seconds, but 30-60 seconds is usually
# enough for duplicate detection.
FINGERPRINT_LENGTH = 60


# Similarity thresholds.
# These should be tuned with your own videos.
STRONG_MATCH = 0.90
LIKELY_MATCH = 0.80


@lru_cache(maxsize=1024)
def acoustic_fingerprint(path):
    """
    Generate a Chromaprint fingerprint locally.

    No AcoustID / internet lookup is performed.

    Returns:
        (duration, fingerprint)
    or:
        None if fingerprinting failed.
    """

    try:
        duration, fingerprint = acoustid.fingerprint_file(
            path,
            maxlength=FINGERPRINT_LENGTH,
            force_fpcalc=True,
        )

        return duration, fingerprint

    except Exception as e:
        print(f"Could not fingerprint: {path}")
        print(f"  Error: {e}")
        return None


def compare_acoustic_fingerprints(fp1, fp2):
    """
    Compare two locally generated Chromaprint fingerprints.

    Returns a dictionary with the similarity score and decision.
    """

    result = {
        "similarity": 0.0,
        "confidence": "unknown",
        "same": False,
        "reason": None,
    }

    if not fp1:
        result["reason"] = "Could not fingerprint video 1."
        return result

    if not fp2:
        result["reason"] = "Could not fingerprint video 2."
        return result

    try:
        similarity = acoustid.compare_fingerprints(
            fp1,
            fp2,
        )

    except Exception as e:
        result["reason"] = f"Fingerprint comparison failed: {e}"
        return result

    if similarity >= STRONG_MATCH:
        confidence = "same"
        same = True

    elif similarity >= LIKELY_MATCH:
        confidence = "likely"
        same = False

    else:
        confidence = "different"
        same = False

    result.update(
        {
            "similarity": similarity,
            "confidence": confidence,
            "same": same,
        }
    )

    return result


def acoustic_compare(path1, path2):
    """
    Fingerprint two videos and compare their audio.

    Everything happens locally.
    No AcoustID database lookup is performed.
    """

    fingerprint1 = acoustic_fingerprint(path1)
    fingerprint2 = acoustic_fingerprint(path2)

    return compare_acoustic_fingerprints(
        fingerprint1,
        fingerprint2,
    )


def compare_vids(path1, path2):
    video1 = path1
    video2 = path2

    result = acoustic_compare(
        video1,
        video2,
    )
    return result["similarity"]
