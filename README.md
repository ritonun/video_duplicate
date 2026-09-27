# Video Duplicate

Tool to detect duplicate videos.

## Install
Dependencies:
```bash
sudo apt install libchromaprint-tools
```

## Usage
```python

folders = [Path("path/to/folder1"), Path("path/to/folder2")]
duplicates = load_probable_duplicate(folders, tolerance=2.0)
print(f"Found {len(duplicates)} duplicates")

for duplicate in duplicates:
    v1, v2 = duplicate
    if check_if_video_duplicate_quick_hash(v1, v2, size=1024 * 1024):
        # check if the first 1MB (size) has the same hash between the two videos
        print(f"{v1} & {v2} are duplicate.")
        continue

    # compare audio between the two video
    result = acoustic_compare_two_videos(v1, v2)
    if result.similarity > 0.9:
        print(f"{v1} & {v2} are duplicate.")
        continue
    elif result.similarity > 0.8:
        print(f"{v1} & {v2} are likely duplicate.")
        continue

    if check_if_duplicate_videos_phash(v1, v2):
        # best method but very long/computer intensive
        print(f"{v1} & {v2} are duplicate.")

    else:
        print(f"{v1} & {v2} are NOT duplicate.")
```