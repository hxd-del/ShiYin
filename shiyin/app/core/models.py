"""应用层数据模型。

Track 是界面、服务、数据库之间唯一的数据契约；上游 SongInfo 只在适配层出现。
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

LOSSLESS_EXTS = {"flac", "wav", "alac", "ape", "wv", "tta", "dsf", "dff"}

_BRACKET_RE = re.compile(r"[（(\[].*?[)）\]]|\s+", re.UNICODE)


def normalize_text(value: str) -> str:
    """歌名/歌手归一化：去掉括号补充说明、空白与大小写差异。"""
    if not value:
        return ""
    value = _BRACKET_RE.sub("", str(value)).strip().lower()
    value = re.sub(r"[^\w\u4e00-\u9fff]+", "", value)
    return value


@dataclass
class Track:
    """一首歌。本地文件与在线直链共用同一个模型。"""

    title: str
    artist: str = ""
    album: str = ""
    source: str = "local"
    source_id: str = ""
    duration_ms: int = 0
    ext: str = ""
    bitrate: int = 0
    size_bytes: int = 0
    url: str = ""
    path: str = ""
    cover_url: str = ""
    lyric: str = ""
    protocol: str = "HTTP"
    track_id: str = ""
    raw: Any = field(default=None, repr=False, compare=False)
    # 跨源归并后挂在该条目下的其他可用源，试听/下载失败时可换源重试
    alternatives: list["Track"] = field(default_factory=list, repr=False, compare=False)

    @property
    def id(self) -> str:
        """稳定主键：下载落盘后不能变，否则库里会出现两条同一首歌。"""
        if self.track_id:
            return self.track_id
        if self.path and (self.source == "local" or not self.source_id):
            return "local:" + hashlib.sha1(self.path.encode("utf-8")).hexdigest()[:16]
        if self.source and self.source_id:
            key = f"{self.source}:{self.source_id}"
        else:
            key = f"{self.source}:{self.source_id}:{self.title}:{self.artist}"
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    @property
    def is_local(self) -> bool:
        if not self.path:
            return False
        return self.source == "local" or os.path.exists(self.path)

    @property
    def is_lossless(self) -> bool:
        return self.ext.lower().lstrip(".") in LOSSLESS_EXTS

    @property
    def ext_clean(self) -> str:
        return (self.ext or "").lower().lstrip(".") or "mp3"

    @property
    def duration_text(self) -> str:
        if not self.duration_ms:
            return "--:--"
        seconds = max(0, self.duration_ms // 1000)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    @property
    def size_text(self) -> str:
        if not self.size_bytes:
            return "--"
        mb = self.size_bytes / 1024 / 1024
        return f"{mb:.1f} MB" if mb >= 1 else f"{self.size_bytes / 1024:.0f} KB"

    @property
    def quality_text(self) -> str:
        if self.bitrate >= 1000:
            return f"{self.bitrate / 1000:.1f} Mbps"
        if self.bitrate:
            return f"{self.bitrate} kbps"
        return self.ext_clean.upper()

    @property
    def display(self) -> str:
        return f"{self.title} - {self.artist}" if self.artist else self.title

    @property
    def quality_score(self) -> int:
        score = 0
        if self.is_lossless:
            score += 1_000_000
        score += min(self.bitrate or 0, 999) * 100
        score += min(self.size_bytes // 1024, 99_999)
        return score

    @property
    def merge_key(self) -> tuple[str, str, int]:
        """跨源归并键：歌名 + 主歌手 + 时长（3 秒容差）。"""
        return (normalize_text(self.title), normalize_text(self.artist.split("/")[0]),
                int(round((self.duration_ms or 0) / 3000)))

    def to_dict(self) -> dict:
        data = dataclasses.asdict(self)
        data.pop("raw", None)
        data.pop("alternatives", None)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Track":
        """从会话/缓存 JSON 还原 Track；只信任白名单字段，不恢复直链与 raw。"""
        allowed = {
            "title", "artist", "album", "source", "source_id", "duration_ms", "ext",
            "bitrate", "size_bytes", "path", "cover_url", "protocol", "track_id",
        }
        values = {k: data[k] for k in allowed if k in data}
        values.setdefault("title", "未知曲目")
        return cls(**values)

    @classmethod
    def from_songinfo(cls, song: Any) -> "Track":
        """把上游 SongInfo 映射为 Track，不触碰 DRM 相关字段。"""
        duration_s = getattr(song, "duration_s", 0) or 0
        url = getattr(song, "download_url", "")
        return cls(
            title=str(getattr(song, "song_name", "") or "未知曲目").strip(),
            artist=str(getattr(song, "singers", "") or "").strip(),
            album=str(getattr(song, "album", "") or "").strip(),
            source=str(getattr(song, "source", "") or getattr(song, "root_source", "") or ""),
            source_id=str(getattr(song, "identifier", "") or ""),
            duration_ms=int(duration_s * 1000),
            ext=str(getattr(song, "ext", "") or "").lower().lstrip("."),
            bitrate=int(getattr(song, "bitrate", 0) or 0),
            size_bytes=int(getattr(song, "file_size_bytes", 0) or 0),
            url=url if isinstance(url, str) else "",
            cover_url=str(getattr(song, "cover_url", "") or ""),
            lyric=str(getattr(song, "lyric", "") or ""),
            protocol=str(getattr(song, "protocol", "HTTP") or "HTTP").upper(),
            raw=song,
        )


class DownloadStatus:
    QUEUED = "queued"
    RESOLVING = "resolving"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    VERIFYING = "verifying"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    LABELS = {
        QUEUED: "等待中",
        RESOLVING: "解析中",
        DOWNLOADING: "下载中",
        PAUSED: "已暂停",
        VERIFYING: "校验中",
        DONE: "已完成",
        FAILED: "失败",
        CANCELLED: "已取消",
    }


@dataclass
class DownloadTask:
    task_id: str
    track: Track
    status: str = DownloadStatus.QUEUED
    progress_bytes: int = 0
    total_bytes: int = 0
    error: str = ""
    attempts: int = 0
    dest_path: str = ""
    created_at: float = field(default_factory=time.time)
    finished_at: float = 0.0
    speed_bps: float = 0.0

    @property
    def percent(self) -> int:
        if self.total_bytes <= 0:
            return 0
        return min(100, int(self.progress_bytes * 100 / self.total_bytes))

    @property
    def status_text(self) -> str:
        return DownloadStatus.LABELS.get(self.status, self.status)

    @property
    def speed_text(self) -> str:
        if self.speed_bps <= 0:
            return "--"
        return f"{self.speed_bps / 1024 / 1024:.1f} MB/s"


@dataclass
class SearchResult:
    keyword: str
    items: list[Track] = field(default_factory=list)
    per_source: dict[str, int] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    elapsed_ms: int = 0

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def summary(self) -> str:
        parts = [f"{src} {cnt}" for src, cnt in sorted(self.per_source.items()) if cnt]
        base = f"共 {self.total} 条"
        if parts:
            base += "（" + "、".join(parts) + "）"
        if self.errors:
            base += f"，{len(self.errors)} 个源失败"
        return base
