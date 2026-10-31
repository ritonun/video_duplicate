# Video Duplicate

Tool to detect duplicate videos.

## Install
Dependencies:
```bash
sudo apt install libchromaprint-tools
```
Python dependencies:
```bash
pip install pyacoustid videohash pillow
```

## Usage
```python
video-duplicate -r 90 -c path/to/cache path/to/folders path/to/trash
```