"""本地流缓存代理。

播放器只认 http://127.0.0.1:<port>/stream/<id>，代理负责：
1. 把会过期的直链包装成稳定地址；
2. 边下边播，支持 Range（拖动进度条不必等整首下完）；
3. 落盘缓存 + LRU 淘汰，试听过的完整文件可直接转为正式下载。
"""

from __future__ import annotations

import os
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

import requests

from shiyin.app.core.models import Track

MIME_TYPES = {
    "mp3": "audio/mpeg", "flac": "audio/flac", "wav": "audio/wav", "m4a": "audio/mp4",
    "aac": "audio/aac", "ogg": "audio/ogg", "opus": "audio/opus", "wma": "audio/x-ms-wma",
    "ape": "audio/x-ape", "wv": "audio/x-wavpack", "m4a": "audio/mp4",
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class StreamEntry:
    def __init__(self, entry_id: str, track: Track, url: str, ext: str, root: Path, ttl_seconds: int):
        self.id = entry_id
        self.track = track
        self.url = url
        self.ext = ext or "mp3"
        self.root = root
        self.part_path = root / f"{entry_id}.part"
        self.final_path = root / f"{entry_id}.{self.ext}"
        self.total = 0
        self.downloaded = 0
        self.done = False
        self.error = ""
        self.cancelled = False
        self.expires_at = time.monotonic() + ttl_seconds
        self.last_used = time.monotonic()
        self.readers = 0
        self.cond = threading.Condition()

    @property
    def data_path(self) -> Path:
        return self.final_path if self.done else self.part_path

    @property
    def name(self) -> str:
        return f"{self.id}.{self.ext}"

    def touch(self) -> None:
        self.last_used = time.monotonic()


class StreamCache:
    def __init__(self, root: str | Path, limit_bytes: int = 2 * 1024 ** 3,
                 ttl_seconds: int = 25 * 60,
                 resolver: Optional[Callable[[Track], str]] = None,
                 port: int = 0):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.limit_bytes = int(limit_bytes)
        self.ttl_seconds = int(ttl_seconds)
        self.resolver = resolver
        self._entries: dict[str, StreamEntry] = {}
        self._lock = threading.Lock()
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._port = port

    # ---------------- 生命周期 ----------------
    def start(self) -> int:
        if self._server:
            return self._port
        cache = self

        class Handler(_StreamHandler):
            pass

        self._server = ThreadingHTTPServer(("127.0.0.1", self._port), Handler)
        self._server.daemon_threads = True
        self._server.cache = cache  # type: ignore[attr-defined]
        self._port = self._server.server_address[1]
        self._thread = threading.Thread(target=self._server.serve_forever, name="stream-cache", daemon=True)
        self._thread.start()
        # 启动时清空缓存目录（每次启动都是干净的）
        self._clear_cache_dir()
        return self._port

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        with self._lock:
            for entry in self._entries.values():
                entry.cancelled = True
        self._entries.clear()
        # 退出时清空缓存目录
        self._clear_cache_dir()

    @property
    def port(self) -> int:
        return self._port

    # ---------------- 对外接口 ----------------
    def _estimate_size(self, track: Track) -> int:
        """根据歌曲时长和比特率估算文件大小"""
        duration_s = (track.duration_ms or 0) / 1000.0
        bitrate = track.bitrate or 128
        if duration_s > 0:
            return int(duration_s * bitrate * 1000 / 8)
        return 0

    def register(self, track: Track, ext: str | None = None) -> tuple[StreamEntry, str]:
        """登记一首歌的试听流，返回 (entry, 本地 URL)。"""
        ext = (ext or track.ext_clean).lower().lstrip(".")
        expected_size = self._estimate_size(track)
        with self._lock:
            existing = self._entries.get(track.id)
            if existing and not existing.error and existing.done and existing.final_path.exists():
                # 校验文件大小：如果实际大小远小于预期（不到 50%），说明是不完整缓存，重新下载
                actual_size = existing.final_path.stat().st_size
                if expected_size > 0 and actual_size < expected_size * 0.5:
                    print(f"[缓存] 文件不完整 ({actual_size} < {expected_size} * 0.5)，重新下载")
                    existing.cancelled = True
                    existing.error = "文件不完整"
                    existing = None
            if existing and not existing.error and (not existing.done or existing.final_path.exists()):
                existing.touch()
                return existing, self._local_url(existing)
            entry = StreamEntry(track.id, track, track.url, ext, self.root, self.ttl_seconds)
            self._entries[track.id] = entry
        thread = threading.Thread(target=self._download, args=(entry,), name=f"stream-{entry.id[:6]}", daemon=True)
        thread.start()
        return entry, self._local_url(entry)

    def entry(self, entry_id: str) -> Optional[StreamEntry]:
        with self._lock:
            return self._entries.get(entry_id)

    def adopt(self, entry: StreamEntry) -> Optional[str]:
        """把已完整缓存的试听文件转成正式下载，返回文件路径。"""
        if entry.done and entry.final_path.exists():
            return str(entry.final_path)
        return None

    def stats(self) -> dict:
        with self._lock:
            done = [e for e in self._entries.values() if e.done]
            return {
                "entries": len(self._entries),
                "complete": len(done),
                "bytes": sum(e.final_path.stat().st_size for e in done if e.final_path.exists()),
            }

    # ---------------- 内部实现 ----------------
    def _local_url(self, entry: StreamEntry) -> str:
        return f"http://127.0.0.1:{self._port}/stream/{entry.id}/{entry.name}"

    def _download(self, entry: StreamEntry) -> None:
        attempt = 0
        max_attempts = 3  # 增加重试次数
        while attempt < max_attempts:
            attempt += 1
            try:
                self._download_once(entry)
                if entry.done:
                    break
            except Exception as err:
                entry.error = f"{type(err).__name__}: {err}"[:200]
                print(f"[缓存] 下载失败 (尝试 {attempt}/{max_attempts}): {entry.error}")
            if entry.cancelled:
                return
            # 可能是直链过期（403/404），重新解析一次
            if attempt < max_attempts and self.resolver is not None:
                # 等待一段时间再重试
                time.sleep(0.5 * attempt)
                try:
                    new_url = self.resolver(entry.track)
                    if new_url:
                        entry.url = new_url
                        entry.error = ""
                        print(f"[缓存] 重新解析直链成功，继续下载")
                        continue
                except Exception as err:
                    entry.error = f"重新解析直链失败: {err}"[:200]
                    print(f"[缓存] {entry.error}")
        with entry.cond:
            entry.cond.notify_all()

    def _download_once(self, entry: StreamEntry) -> None:
        headers = {"User-Agent": UA}
        with requests.get(entry.url, headers=headers, stream=True, timeout=(10, 30)) as resp:
            if resp.status_code in (403, 404, 410):
                raise RuntimeError(f"直链失效 HTTP {resp.status_code}")
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length") or 0)
            with entry.cond:
                entry.total = total
                entry.cond.notify_all()
            received = 0
            with open(entry.part_path, "wb") as fp:
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if entry.cancelled:
                        raise RuntimeError("cancelled")
                    if not chunk:
                        continue
                    fp.write(chunk)
                    received += len(chunk)
                    with entry.cond:
                        entry.downloaded = received
                        entry.cond.notify_all()
        if entry.total and received != entry.total:
            raise RuntimeError(f"字节数不一致: {received}/{entry.total}")
        # 重命名文件：添加重试机制，等待播放器释放文件句柄
        for retry in range(5):
            try:
                os.replace(entry.part_path, entry.final_path)
                break
            except PermissionError:
                if retry < 4:
                    time.sleep(0.2)  # 等待 200ms 后重试
                else:
                    # 最后一次尝试失败，复制而不是移动
                    import shutil
                    shutil.copy2(entry.part_path, entry.final_path)
                    try:
                        entry.part_path.unlink()
                    except Exception:
                        pass  # 忽略删除临时文件的错误
        with entry.cond:
            entry.done = True
            entry.total = received
            entry.cond.notify_all()
        self._evict()

    def _clear_cache_dir(self) -> None:
        """清空缓存目录中的所有文件"""
        for item in self.root.glob("*"):
            try:
                if item.is_file():
                    item.unlink()
            except OSError:
                pass
        print(f"[缓存] 已清空缓存目录")

    def _cleanup_stale_files(self) -> None:
        for item in self.root.glob("*.part"):
            try:
                if time.time() - item.stat().st_mtime > 24 * 3600:
                    item.unlink()
            except OSError:
                pass

    def _evict(self) -> None:
        with self._lock:
            done = [e for e in self._entries.values() if e.done and e.readers == 0]
            total = sum(e.final_path.stat().st_size for e in done if e.final_path.exists())
            for entry in sorted(done, key=lambda e: e.last_used):
                if total <= self.limit_bytes:
                    break
                try:
                    size = entry.final_path.stat().st_size
                    entry.final_path.unlink()
                    total -= size
                    self._entries.pop(entry.id, None)
                except OSError:
                    continue

    def serve(self, handler: BaseHTTPRequestHandler, entry: StreamEntry, start: int, end: int | None) -> None:
        entry.readers += 1
        try:
            total = entry.total or None
            # 当 total 未知时，用已下载大小或歌曲信息估算
            if not total:
                if entry.downloaded > 0:
                    total = entry.downloaded
                else:
                    duration_s = (entry.track.duration_ms or 0) / 1000.0
                    bitrate = entry.track.bitrate or 128
                    if duration_s > 0:
                        total = int(duration_s * bitrate * 1000 / 8)
            if total and start >= total:
                handler.send_response(416)
                handler.send_header("Content-Range", f"bytes */{total}")
                handler.send_header("Content-Length", "0")
                handler.end_headers()
                return
            last = end if end is not None else (total - 1 if total else None)
            partial = start > 0 or (end is not None and total is not None and end < total - 1)
            handler.send_response(206 if partial else 200)
            handler.send_header("Content-Type", MIME_TYPES.get(entry.ext, "application/octet-stream"))
            handler.send_header("Accept-Ranges", "bytes")
            if total:
                length = (last - start + 1) if last is not None else (total - start)
                handler.send_header("Content-Length", str(max(0, length)))
                if partial:
                    handler.send_header("Content-Range", f"bytes {start}-{start + length - 1}/{total}")
            else:
                handler.send_header("Connection", "close")
            handler.end_headers()

            pos = start
            fp = None
            try:
                if entry.data_path.exists():
                    fp = open(entry.data_path, "rb")
                while fp is not None:
                    with entry.cond:
                        deadline = time.monotonic() + 20
                        while entry.downloaded <= pos and not entry.done and not entry.error \
                                and not entry.cancelled and time.monotonic() < deadline:
                            entry.cond.wait(0.2)
                        available = entry.downloaded
                    if pos >= available:
                        break
                    fp.seek(pos)
                    length = min(256 * 1024, available - pos)
                    data = fp.read(length)
                    if not data:
                        break
                    try:
                        handler.wfile.write(data)
                    except (BrokenPipeError, ConnectionResetError):
                        break
                    pos += len(data)
                    if last is not None and pos > last:
                        break
            finally:
                if fp is not None:
                    fp.close()
        finally:
            entry.readers -= 1
            entry.touch()


class _StreamHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ShiYinStream/1.0"

    def log_message(self, fmt, *args):
        return

    def do_HEAD(self):
        """HEAD 请求：等待获取文件大小后再响应"""
        cache: StreamCache = getattr(self.server, "cache")
        match = re.match(r"^/stream/([0-9a-f]+)", urlparse(self.path).path)
        entry = cache.entry(match.group(1)) if match else None
        if entry is None:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        entry.touch()
        # 等待文件大小确定或有下载进度（最多 15 秒）
        deadline = time.monotonic() + 15.0
        while not entry.total and entry.downloaded == 0 and not entry.error \
                and not entry.cancelled and time.monotonic() < deadline:
            with entry.cond:
                entry.cond.wait(0.1)
        if entry.error or entry.cancelled:
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        total = entry.total or None
        # 当源服务器未返回 Content-Length 时，用歌曲时长和比特率估算文件大小
        if not total:
            duration_s = (entry.track.duration_ms or 0) / 1000.0
            bitrate = entry.track.bitrate or 128  # 默认 128kbps
            if duration_s > 0:
                total = int(duration_s * bitrate * 1000 / 8)
        self.send_response(200)
        self.send_header("Content-Type", MIME_TYPES.get(entry.ext, "application/octet-stream"))
        self.send_header("Accept-Ranges", "bytes")
        if total:
            self.send_header("Content-Length", str(total))
        self.end_headers()

    def do_GET(self, head_only: bool = False):
        cache: StreamCache = getattr(self.server, "cache")
        match = re.match(r"^/stream/([0-9a-f]+)", urlparse(self.path).path)
        entry = cache.entry(match.group(1)) if match else None
        if entry is None:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        entry.touch()
        start, end = 0, None
        header = self.headers.get("Range")
        if header:
            m = re.match(r"bytes=(\d+)-(\d*)", header.strip())
            if m:
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else None
        # 等待文件创建且有数据（最多 15 秒）
        deadline = time.monotonic() + 15.0
        while (not entry.data_path.exists() or entry.downloaded == 0) \
                and not entry.error and not entry.cancelled and time.monotonic() < deadline:
            with entry.cond:
                entry.cond.wait(0.1)
        if entry.error:
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if entry.cancelled:
            self.send_response(503)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        cache.serve(self, entry, start, end)


def new_entry_id() -> str:
    return uuid.uuid4().hex[:16]
