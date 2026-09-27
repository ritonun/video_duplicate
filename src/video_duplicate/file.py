# file.py
import os

from video_duplicate import get_duration


def load_probable_duplicate(path1, path2, tolerance=2.0):

    duplicates = []

    videos1 = load_videos(path1)
    videos2 = load_videos(path2)

    for video1 in videos1:
        duration1 = get_duration(video1)

        for video2 in videos2:
            duration2 = get_duration(video2)

            if abs(duration1 - duration2) <= tolerance:
                duplicates.append([video1, video2])

    return duplicates


def load_videos(path: str):
    videos = []
    files = os.listdir(path)
    for file in files:
        videos.append(os.path.join(path, file))
    return videos


def write_to_csv(va, vb, line):
    full_line = va.split("/")[-1] + ";" + vb.split("/")[-1] + ";" + line
    if not full_line.endswith("\n"):
        full_line += "\n"
    with open("data/result.csv", "a") as f:
        f.write(full_line)
