# src/video_duplicate/utils.py

import subprocess
from pathlib import Path


def get_duration(path: Path | str) -> float | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return float(result.stdout.strip())
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        ValueError,
        OSError,
    ) as e:
        print(f"Could not read duration: {path}\n  Reason: {e}")
        return None
