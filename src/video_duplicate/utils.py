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


class Progress:
    def __init__(self, total, current=1):
        self.total = total
        self.current = current

    def update(self, current_add=1, total_add=0) -> None:
        self.current += current_add
        self.total += total_add

    def get_percent(self) -> float:
        percent = self.current / self.total * 100
        return round(percent, 1)

    def get_str(self) -> str:
        return f"{self.current}/{self.total} {self.get_percent()}%"
