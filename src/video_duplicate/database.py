# src/video_duplicate/database.py

import sqlite3
from dataclasses import dataclass
from enum import Enum


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
    url: str
    creator: str
    qhash: bytes
    audio: bytes
    phash: str
    runtime: float
    status: Status


class DB:
    def __init__(self, db_path: str) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def __enter__(self):
        """necessary to use with openDB()"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """necessary to use with openDB()"""
        self.close()

    def close(self):
        """Properly close database"""
        self.conn.close()

    def init_database(self):
        self.conn.execute(CREATE_VIDEOS_TABLE)
        self.conn.commit()

    def get_video(
        self,
        path: str | None = None,
        creator: str | None = None,
        name: str | None = None,
    ) -> Video | None:
        if path is not None:
            cursor = self.conn.execute(
                "SELECT * FROM videos WHERE path = ?",
                (path,),
            )

        if creator is not None and name is not None:
            cursor = self.conn.execute(
                "SELECT * FROM videos WHERE creator = ? AND name = ?",
                (creator, name),
            )

        else:
            raise ValueError("Provide either a path or both creator and name")
        row = cursor.fetchone()
        if row is None:
            return None

        return Video(
            id=row["id"],
            path=row["path"],
            name=row["name"],
            url=row["url"],
            creator=row["creator"],
            qhash=row["qhash"],
            audio=row["audio"],
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
    qhash BLOB,
    audio BLOB,
    phash TEXT,
    runtime REAL,
    status TEXT NOT NULL DEFAULT 'pending',
    UNIQUE(creator, name)
)
"""
