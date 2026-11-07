# srv/video-duplicate/database.py

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Status(Enum):
    PENDING = "pending"
    OK = "ok"
    DELETED = "deleted"
    OPTIMIZED = "optimized"


@dataclass
class Video:
    id: int
    path: str
    name: str
    url: str | None
    creator: str
    qhash: str | None
    audio: bytes | None
    audio_duration: float | None
    phash: str | None
    runtime: float | None
    status: Status


class DB:
    """Persistence layer for video analysis results."""

    def __init__(self, db_path: str | Path) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_database()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def close(self) -> None:
        """Properly close the database connection."""
        self.conn.close()

    def init_database(self) -> None:
        """Create the database schema if it does not already exist."""
        self.conn.execute(CREATE_VIDEOS_TABLE)
        self.conn.commit()

    def get_video(self, path: str | Path) -> Video | None:
        """Return a video by its full path."""

        path = str(path)

        cursor = self.conn.execute(
            "SELECT * FROM videos WHERE path = ?",
            (path,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_video(row)

    def get_or_create_video(
        self,
        path: str | Path,
        creator: str | None = None,
        runtime: float | None = None,
    ) -> Video:
        """Return an existing video or create a new database record."""

        path = Path(path)

        video = self.get_video(path)
        if video is not None:
            return video

        if creator is None:
            creator = path.parent.name

        self.conn.execute(
            """
            INSERT INTO videos (path, name, creator, runtime)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(path),
                path.name,
                creator,
                runtime,
            ),
        )
        self.conn.commit()

        video = self.get_video(path)

        if video is None:
            raise RuntimeError(f"Failed to create video record for {path}")

        return video

    def update_video(
        self,
        path: str | Path,
        *,
        qhash: str | None = None,
        audio: bytes | None = None,
        audio_duration: float | None = None,
        phash: str | None = None,
        runtime: float | None = None,
        status: Status | None = None,
    ) -> None:
        """Update one or more analysis results for a video."""

        path = str(path)
        self.get_or_create_video(path)

        fields: dict[str, object] = {}

        if qhash is not None:
            fields["qhash"] = qhash

        if audio is not None:
            fields["audio"] = audio

        if audio_duration is not None:
            fields["audio_duration"] = audio_duration

        if phash is not None:
            fields["phash"] = phash

        if runtime is not None:
            fields["runtime"] = runtime

        if status is not None:
            fields["status"] = status.value

        if not fields:
            return

        assignments = ", ".join(f"{column} = ?" for column in fields)
        values = list(fields.values())
        values.append(path)

        self.conn.execute(
            f"""
            UPDATE videos
            SET {assignments}
            WHERE path = ?
            """,
            values,
        )
        self.conn.commit()

    def remove_missing_files(self) -> int:
        """Remove database records whose files no longer exist."""

        cursor = self.conn.execute("SELECT id, path FROM videos")
        rows = cursor.fetchall()

        missing_ids = [row["id"] for row in rows if not Path(row["path"]).exists()]

        if not missing_ids:
            return 0

        placeholders = ", ".join("?" for _ in missing_ids)

        self.conn.execute(
            f"DELETE FROM videos WHERE id IN ({placeholders})",
            missing_ids,
        )
        self.conn.commit()

        return len(missing_ids)

    @staticmethod
    def _row_to_video(row: sqlite3.Row) -> Video:
        """Convert a SQLite row into a Video model."""

        return Video(
            id=row["id"],
            path=row["path"],
            name=row["name"],
            url=row["url"],
            creator=row["creator"],
            qhash=row["qhash"],
            audio=row["audio"],
            audio_duration=row["audio_duration"],
            phash=row["phash"],
            runtime=row["runtime"],
            status=Status(row["status"]),
        )


CREATE_VIDEOS_TABLE = """
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    url TEXT,
    creator TEXT NOT NULL,
    qhash TEXT,
    audio BLOB,
    audio_duration REAL,
    phash TEXT,
    runtime REAL,
    status TEXT NOT NULL DEFAULT 'pending',
    UNIQUE(creator, name)
)
"""
