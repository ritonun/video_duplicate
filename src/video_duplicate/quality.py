# src/video_duplicate/quality.py

import os
import json
import subprocess

# Codec efficiency multipliers. Modern codecs get a boost.
CODEC_MULTIPLIERS = {
    "av1": 2.0,
    "hevc": 1.5,  # H.265
    "vp9": 1.4,
    "h264": 1.0,  # Baseline
    "vp8": 0.8,
    "mpeg4": 0.5,
}


def get_video_stats(filepath):
    """Uses ffprobe to extract resolution, fps, codec, and gets file size."""
    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        filepath,
    ]

    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        data = json.loads(result.stdout)

        # Find the video stream
        video_stream = next(
            (s for s in data.get("streams", []) if s["codec_type"] == "video"), None
        )
        if not video_stream:
            return None

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        codec = video_stream.get("codec_name", "unknown").lower()

        # FPS often comes as a fraction string like "30000/1001" or "60/1"
        fps_string = video_stream.get("avg_frame_rate", "0/1")
        num, den = map(int, fps_string.split("/"))
        fps = num / den if den != 0 else 0

        # Get actual file size in MB directly from the OS (most accurate)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        return {
            "path": filepath,
            "width": width,
            "height": height,
            "codec": codec,
            "fps": fps,
            "size_mb": size_mb,
        }
    except Exception as e:
        print(f"[!] Failed to read stats for {filepath}: {e}")
        return None


def pick_best_video(path1, path2, quality_margin=1.15, size_savings_margin=0.70):
    """
    Compares two videos and returns the path of the one to keep.

    quality_margin: 1.15 means if Q1 is within 15% of Q2, they are "visually similar".
    size_savings_margin: 0.70 means if the smaller file is 30% smaller, prefer it.
    """
    v1 = get_video_stats(path1)
    v2 = get_video_stats(path2)

    if not v1 or not v2:
        return path1 if v1 else path2  # Fallback if one is broken

    # Calculate Quality Scores
    c_mult1 = CODEC_MULTIPLIERS.get(v1["codec"], 1.0)
    c_mult2 = CODEC_MULTIPLIERS.get(v2["codec"], 1.0)

    score1 = (v1["width"] * v1["height"]) * v1["fps"] * c_mult1
    score2 = (v2["width"] * v2["height"]) * v2["fps"] * c_mult2

    # Identify which is mathematically "higher quality" and which is "smaller"
    higher_q, lower_q = (v1, v2) if score1 >= score2 else (v2, v1)
    higher_score, lower_score = max(score1, score2), min(score1, score2)

    # If the lower quality video is practically identical in quality (within margin)...
    if higher_score <= (lower_score * quality_margin):
        # ...check if the lower quality one saves us significant space.
        if lower_q["size_mb"] <= (higher_q["size_mb"] * size_savings_margin):
            print(
                f"Keeping smaller file: {lower_q['path']} (Saved {higher_q['size_mb'] - lower_q['size_mb']:.1f} MB)"
            )
            return lower_q["path"]

    # Otherwise, raw quality wins
    return higher_q["path"]


def pick_worst_video(path1, path2, quality_margin=1.15, size_savings_margin=0.70):
    v1 = get_video_stats(path1)
    v2 = get_video_stats(path2)

    if not v1 or not v2:
        return path1 if v1 else path2  # Fallback if one is broken

    r = pick_best_video(
        path1,
        path2,
        quality_margin=quality_margin,
        size_savings_margin=size_savings_margin,
    )
    if r == path1:
        return path2
    elif r == path2:
        return path1
