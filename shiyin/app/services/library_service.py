"""本地库：扫描目录、读标签、计算指纹、写库。"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable, Iterable

from shiyin.app.core.models import Track

AUDIO_EXTS = {
    ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".ape", ".wv",
    ".tta", ".dsf", ".dff", ".wma", ".aiff", ".aif", ".mka", ".webm",
}


def fingerprint(path: Path) -> str:
    """文件大小 + 首尾各 64 KB 哈希，成本远低于整文件哈希。"""
    size = path.stat().st_size
    digest = hashlib.sha1(str(size).encode("utf-8"))
    with open(path, "rb") as fp:
        digest.update(fp.read(65536))
        if size > 131072:
            fp.seek(-65536, os.SEEK_END)
            digest.update(fp.read(65536))
    return digest.hexdigest()[:20]


def read_tags(path: Path) -> dict:
    try:
        import mutagen

        audio = mutagen.File(str(path), easy=True)
        if not audio:
            return {}
        info = {
            "title": (audio.get("title") or [""])[0],
            "artist": (audio.get("artist") or [""])[0],
            "album": (audio.get("album") or [""])[0],
            "duration_ms": int((audio.info.length if getattr(audio, "info", None) else 0) * 1000),
        }
        return info
    except Exception:
        return {}


def read_lyric(path: Path) -> tuple[str, str]:
    """读取音频同目录的 .lrc；返回 (歌词文本, 歌词文件路径)。

    下载歌词时写的是 UTF-8，但用户自己的 lrc 也可能是 GBK/GB18030，
    所以逐编码尝试，读不到就返回空，不影响扫描。
    """
    for candidate in (path.with_suffix(".lrc"), path.with_suffix(".LRC")):
        if not candidate.exists():
            continue
        try:
            raw = candidate.read_bytes()
        except OSError:
            continue
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                text = raw.decode(encoding)
            except UnicodeDecodeError:
                continue
            if text.strip():
                return text, str(candidate)
            return "", str(candidate)
    return "", ""


class LibraryService:
    def __init__(self, repository, covers_dir: str | Path | None = None):
        self.repository = repository
        self.covers_dir = Path(covers_dir) if covers_dir else None

    def scan(self, directory: str | Path,
             on_progress: Callable[[int, int, str], None] | None = None) -> dict:
        root = Path(directory)
        if not root.exists():
            return {"added": 0, "skipped": 0, "failed": 0, "total": 0}
        files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTS]
        added = skipped = failed = 0
        for index, path in enumerate(files, start=1):
            if on_progress:
                on_progress(index, len(files), path.name)
            try:
                fp = fingerprint(path)
                existing = self.repository.find_local_by_fingerprint(fp)
                if existing:
                    # 文件已经在库里：补一次同目录歌词，老记录不必删库重扫。
                    lyric_text, lyric_path = read_lyric(path)
                    if lyric_text and not existing.lyric:
                        existing.lyric = lyric_text
                        self.repository.upsert_track(
                            existing, fingerprint=fp, lyric_path=lyric_path)
                    skipped += 1
                    continue
                # 下载时先注册的是在线曲目（source 不是 local），同一路径再扫一次
                # 会被当成新文件；按路径命中后只补歌词，避免本地库出现两条。
                by_path = self.repository.find_by_path(str(path))
                if by_path:
                    lyric_text, lyric_path = read_lyric(path)
                    if lyric_text and not by_path.lyric:
                        by_path.lyric = lyric_text
                        self.repository.upsert_track(
                            by_path, fingerprint=fp, lyric_path=lyric_path)
                    skipped += 1
                    continue
                tags = read_tags(path)
                lyric_text, lyric_path = read_lyric(path)
                stat = path.stat()
                track = Track(
                    title=tags.get("title") or path.stem,
                    artist=tags.get("artist") or "",
                    album=tags.get("album") or "",
                    source="local",
                    source_id=fp,
                    duration_ms=int(tags.get("duration_ms") or 0),
                    ext=path.suffix.lower().lstrip("."),
                    size_bytes=stat.st_size,
                    path=str(path),
                    lyric=lyric_text,
                )
                self.repository.upsert_track(track, fingerprint=fp, lyric_path=lyric_path)
                added += 1
            except Exception:
                failed += 1
        return {"added": added, "skipped": skipped, "failed": failed, "total": len(files)}

    def import_files(self, paths: Iterable[str | Path]) -> int:
        added = 0
        for raw in paths:
            path = Path(raw)
            if not path.exists() or path.suffix.lower() not in AUDIO_EXTS:
                continue
            try:
                fp = fingerprint(path)
                existing = self.repository.find_local_by_fingerprint(fp)
                if existing:
                    lyric_text, lyric_path = read_lyric(path)
                    if lyric_text and not existing.lyric:
                        existing.lyric = lyric_text
                        self.repository.upsert_track(existing, fingerprint=fp, lyric_path=lyric_path)
                    continue
                tags = read_tags(path)
                lyric_text, lyric_path = read_lyric(path)
                track = Track(
                    title=tags.get("title") or path.stem,
                    artist=tags.get("artist") or "",
                    album=tags.get("album") or "",
                    source="local",
                    source_id=fp,
                    duration_ms=int(tags.get("duration_ms") or 0),
                    ext=path.suffix.lower().lstrip("."),
                    size_bytes=path.stat().st_size,
                    path=str(path),
                    lyric=lyric_text,
                )
                self.repository.upsert_track(track, fingerprint=fp, lyric_path=lyric_path)
                added += 1
            except Exception:
                continue
        return added
