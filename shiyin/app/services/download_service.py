"""下载服务：队列、并发、断点续传、校验与入库。

Qt 无关：界面通过 snapshot() 轮询（200 ms），这样服务层可以单测。
"""

from __future__ import annotations

import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

import requests

from shiyin.app.core.models import DownloadStatus, DownloadTask, Track

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_ILLEGAL = re.compile(r'[\\/:*?"<>|\r\n]+')


def safe_filename(name: str, fallback: str = "track") -> str:
    cleaned = _ILLEGAL.sub("_", (name or "").strip())[:120].strip(" .")
    return cleaned or fallback


class _Cancelled(Exception):
    pass


class _Control:
    def __init__(self):
        self.cancel = threading.Event()
        self.pause = threading.Event()


class DownloadService:
    def __init__(self, adapter, settings, repository, stream_cache=None, download_dir: str | Path | None = None):
        self.adapter = adapter
        self.settings = settings
        self.repository = repository
        self.stream_cache = stream_cache
        
        # 自动处理下载目录权限
        requested_dir = Path(download_dir or settings.get("download_dir"))
        self.download_dir = self._ensure_writable_dir(requested_dir)
        
        self._tasks: dict[str, DownloadTask] = {}
        self._controls: dict[str, _Control] = {}
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max(1, int(settings.get("concurrency") or 6)))
    
    def _ensure_writable_dir(self, requested: Path) -> Path:
        """确保下载目录可写，如果权限不足则回退到 AppData"""
        try:
            # 尝试创建目录
            requested.mkdir(parents=True, exist_ok=True)
            
            # 测试写入权限
            test_file = requested / ".write_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            
            # 权限正常，使用请求的目录
            return requested
        except (OSError, PermissionError) as e:
            # 权限不足，回退到 AppData
            import os
            fallback = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".local")) / "ShiYin" / "library"
            fallback.mkdir(parents=True, exist_ok=True)
            print(f"[下载] 目录 {requested} 权限不足，已回退到 {fallback}")
            return fallback

    # ---------------- 对外接口 ----------------
    def submit(self, track: Track, priority: int = 0) -> str:
        task_id = uuid.uuid4().hex[:12]
        task = DownloadTask(task_id=task_id, track=track)
        control = _Control()
        with self._lock:
            self._tasks[task_id] = task
            self._controls[task_id] = control
        self.repository.record_download(task)
        thread = threading.Thread(target=self._run, args=(task, control), name=f"dl-{task_id[:6]}", daemon=True)
        thread.start()
        return task_id

    def pause(self, task_id: str) -> None:
        control = self._controls.get(task_id)
        task = self._tasks.get(task_id)
        if control and task and task.status in (DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING):
            control.pause.set()
            task.status = DownloadStatus.PAUSED

    def resume(self, task_id: str) -> None:
        control = self._controls.get(task_id)
        task = self._tasks.get(task_id)
        if control and task and task.status == DownloadStatus.PAUSED:
            control.pause.clear()
            task.status = DownloadStatus.DOWNLOADING

    def cancel(self, task_id: str) -> None:
        control = self._controls.get(task_id)
        task = self._tasks.get(task_id)
        if control and task:
            control.pause.clear()
            control.cancel.set()
            if task.status != DownloadStatus.DONE:
                task.status = DownloadStatus.CANCELLED

    def retry(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if not task:
            return
        control = _Control()
        with self._lock:
            self._controls[task_id] = control
        task.status = DownloadStatus.QUEUED
        task.error = ""
        task.attempts += 1
        threading.Thread(target=self._run, args=(task, control), name=f"dl-{task_id[:6]}", daemon=True).start()

    def snapshot(self) -> list[DownloadTask]:
        with self._lock:
            return sorted(self._tasks.values(), key=lambda t: t.created_at)

    def active_count(self) -> int:
        return sum(1 for t in self._tasks.values()
                   if t.status in (DownloadStatus.RESOLVING, DownloadStatus.DOWNLOADING, DownloadStatus.VERIFYING))

    # ---------------- 执行 ----------------
    def _run(self, task: DownloadTask, control: _Control) -> None:
        with self._semaphore:
            try:
                self._execute(task, control)
            except _Cancelled:
                task.status = DownloadStatus.CANCELLED
            except Exception as err:
                task.status = DownloadStatus.FAILED
                task.error = f"{type(err).__name__}: {err}"[:200]
            finally:
                task.finished_at = time.time()
                self.repository.record_download(task)

    def _execute(self, task: DownloadTask, control: _Control) -> None:
        track = task.track
        task.status = DownloadStatus.RESOLVING
        task.dest_path = task.dest_path or str(self._dest_for(track))
        dest = Path(task.dest_path)

        if dest.exists() and dest.stat().st_size > 0:
            task.status = DownloadStatus.DONE
            task.progress_bytes = task.total_bytes = dest.stat().st_size
            self._register(track, dest)
            return

        # 试听缓存已完整时直接转正，不重复下载
        adopted = self._adopt_from_cache(track, dest)
        if adopted:
            task.status = DownloadStatus.DONE
            task.progress_bytes = task.total_bytes = dest.stat().st_size
            self._register(track, dest)
            return

        if track.protocol.upper() == "HLS":
            task.status = DownloadStatus.DOWNLOADING
            self.adapter.download_hls(track, dest)
            task.progress_bytes = dest.stat().st_size if dest.exists() else 0
            task.total_bytes = task.progress_bytes
        else:
            url = track.url or self.adapter.resolve(track)
            self._http_download(task, control, url, dest)

        task.status = DownloadStatus.VERIFYING
        self._verify(task, dest)
        self._write_tags(dest, track)
        self._register(track, dest)
        task.status = DownloadStatus.DONE
        task.finished_at = time.time()

    def _dest_for(self, track: Track) -> Path:
        base = f"{track.artist} - {track.title}" if track.artist else track.title
        return self.download_dir / f"{safe_filename(base)}.{track.ext_clean}"

    def _adopt_from_cache(self, track: Track, dest: Path) -> bool:
        if not self.stream_cache:
            return False
        entry = self.stream_cache.entry(track.id)
        if not entry or not (entry.done and entry.final_path.exists()):
            return False
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.replace(entry.final_path, dest)
            return True
        except OSError:
            return False

    def _http_download(self, task: DownloadTask, control: _Control, url: str, dest: Path) -> None:
        # 使用系统临时目录下载，避免目标目录权限/锁定问题
        dest.parent.mkdir(parents=True, exist_ok=True)
        ext = dest.suffix or ".tmp"
        fd, part_path = tempfile.mkstemp(suffix=f"{ext}.part", dir=tempfile.gettempdir())
        os.close(fd)  # 立即关闭文件描述符
        part = Path(part_path)
        
        existing = 0
        attempts = 0
        last_error: Optional[Exception] = None
        while attempts < 3:
            attempts += 1
            try:
                task.status = DownloadStatus.DOWNLOADING
                task.attempts = attempts
                headers = {"User-Agent": UA}
                if existing:
                    headers["Range"] = f"bytes={existing}-"
                with requests.get(url, headers=headers, stream=True, timeout=(10, 30)) as resp:
                    if resp.status_code == 416:
                        # 已经下满
                        break
                    if existing and resp.status_code == 200:
                        existing = 0
                    resp.raise_for_status()
                    length = int(resp.headers.get("Content-Length") or 0)
                    task.total_bytes = existing + length if length else task.total_bytes
                    task.progress_bytes = existing
                    mode = "ab" if existing else "wb"
                    last_tick = time.monotonic()
                    last_bytes = existing
                    with open(part, mode) as fp:
                        for chunk in resp.iter_content(chunk_size=64 * 1024):
                            if control.cancel.is_set():
                                raise _Cancelled()
                            while control.pause.is_set() and not control.cancel.is_set():
                                time.sleep(0.2)
                            if not chunk:
                                continue
                            fp.write(chunk)
                            existing += len(chunk)
                            task.progress_bytes = existing
                            now = time.monotonic()
                            if now - last_tick >= 1.0:
                                task.speed_bps = (existing - last_bytes) / (now - last_tick)
                                last_tick, last_bytes = now, existing
                    task.speed_bps = 0
                break
            except _Cancelled:
                raise
            except Exception as err:
                last_error = err
                existing = part.stat().st_size if part.exists() else existing
                time.sleep(min(2 ** attempts, 10))
        if last_error and not part.exists():
            raise last_error
        if task.total_bytes and part.stat().st_size != task.total_bytes:
            raise RuntimeError(f"大小不一致: {part.stat().st_size}/{task.total_bytes}")
        # 从临时目录移动到目标目录
        try:
            os.replace(part, dest)
        except OSError:
            # 跨盘符时 os.replace 可能失败，改用复制后删除
            import shutil
            shutil.copy2(part, dest)
            part.unlink(missing_ok=True)

    def _verify(self, task: DownloadTask, dest: Path) -> None:
        if not dest.exists() or dest.stat().st_size == 0:
            raise RuntimeError("下载结果为空文件")
        if task.total_bytes and dest.stat().st_size != task.total_bytes:
            raise RuntimeError("文件大小与响应头不一致")
        try:
            import filetype

            kind = filetype.guess(str(dest))
            if kind and dest.suffix.lower().lstrip(".") not in {"m4a", "m4b", "mp4"}:
                ok = kind.extension.lower() in {dest.suffix.lower().lstrip("."), "mp3", "flac", "ogg", "wav"}
                if not ok:
                    raise RuntimeError(f"文件头与扩展名不符: {kind.extension} vs {dest.suffix}")
        except ImportError:
            pass

    def _write_tags(self, dest: Path, track: Track) -> None:
        try:
            import mutagen

            audio = mutagen.File(str(dest), easy=True)
            if not audio:
                return
            if track.title:
                audio["title"] = [track.title]
            if track.artist:
                audio["artist"] = [track.artist]
            if track.album:
                audio["album"] = [track.album]
            audio.save()
        except Exception:
            # 标签写入失败不影响文件可用性
            return

    def _register(self, track: Track, dest: Path) -> None:
        track.path = str(dest)
        track.size_bytes = dest.stat().st_size
        # 保存歌词到文件
        lyric_path = ""
        if track.lyric:
            lyric_file = dest.with_suffix(".lrc")
            try:
                lyric_file.write_text(track.lyric, encoding="utf-8")
                lyric_path = str(lyric_file)
            except Exception:
                pass
        self.repository.upsert_track(track, lyric_path=lyric_path)
