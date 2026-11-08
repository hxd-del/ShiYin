"""播放服务：队列、状态机、直链与本地文件的统一加载。"""

from __future__ import annotations

import random
import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from shiyin.app.core.models import Track


class PlaybackService(QObject):
    currentChanged = Signal(object)
    stateChanged = Signal(str)
    queueChanged = Signal()
    failed = Signal(str)

    def __init__(self, backend, stream_cache, settings=None, repository=None, adapter=None, parent=None):
        super().__init__(parent)
        self.backend = backend
        self.stream_cache = stream_cache
        self.settings = settings
        self.repository = repository
        self.adapter = adapter
        self.queue: list[Track] = []
        self.index = -1
        self._loaded_track_id: str | None = None
        self._resume_track_id: str | None = None
        self._resume_position_ms = 0
        self._pending_resume_ms = 0
        self.repeat = (settings.get("repeat_mode") if settings else "off") or "off"
        self.shuffle = False
        # 在线缓存完成后再播放：只把完整文件交给播放器，避免把下载中的 .part
        # 暴露给 Qt（下载重试/变慢/改名都会让播放器收到截断的流）。
        self._play_token = 0
        self._pending_entry = None
        self._pending_token = -1
        self._pending_since = 0.0
        self._pending_timer = QTimer(self)
        self._pending_timer.setInterval(100)
        self._pending_timer.timeout.connect(self._check_pending)
        self.backend.endReached.connect(self._on_end)
        self.backend.errorOccurred.connect(self._on_error)
        self.backend.stateChanged.connect(self.stateChanged.emit)
        if settings:
            self.backend.set_volume(float(settings.get("volume") or 0.8))

    # ---------------- 队列 ----------------
    @property
    def current(self) -> Track | None:
        if 0 <= self.index < len(self.queue):
            return self.queue[self.index]
        return None

    def set_queue(self, tracks: list[Track], index: int = 0) -> None:
        self.queue = list(tracks)
        self.index = max(0, min(index, len(self.queue) - 1)) if self.queue else -1
        self.queueChanged.emit()
        if self.queue:
            self.play_index(self.index)

    def enqueue(self, track: Track, next_up: bool = False) -> None:
        if next_up and 0 <= self.index < len(self.queue):
            self.queue.insert(self.index + 1, track)
        else:
            self.queue.append(track)
        self.queueChanged.emit()

    def clear_queue(self) -> None:
        self._cancel_pending()
        self.queue.clear()
        self.index = -1
        self.backend.stop()
        self.queueChanged.emit()

    def remove_at(self, index: int) -> None:
        """从队列里删掉一首；正在播的那首被删时顺延到下一首。"""
        if not (0 <= index < len(self.queue)):
            return
        self.queue.pop(index)
        if index < self.index:
            self.index -= 1
        elif index == self.index:
            if not self.queue:
                self.index = -1
                self.backend.stop()
            else:
                self.index = min(index, len(self.queue) - 1)
                self.queueChanged.emit()
                self.play_index(self.index)
                return
        self.queueChanged.emit()

    # ---------------- 播放控制 ----------------
    def play_index(self, index: int) -> None:
        if not self.queue:
            return
        self.index = index % len(self.queue)
        track = self.queue[self.index]
        self._play_token += 1
        token = self._play_token
        self._cancel_pending()
        # 先通知 UI 换歌并启动缓冲反馈，再去解析直链/登记缓存；
        # 否则解析慢时播放条还停在上一首，用户会以为双击没反应。
        self.currentChanged.emit(track)
        if self.repository:
            self.repository.add_to_playlist("recent", track)
        resume_ms = 0
        if self._resume_track_id == track.id:
            resume_ms = max(0, self._resume_position_ms)
        self._resume_track_id = None
        self._resume_position_ms = 0
        self._pending_resume_ms = 0
        target = self._resolve_target(track, token)
        if not target:
            # 在线歌曲已登记缓存，等 _check_pending 在下载完成后播放；
            # 无直链/失败时 failed 已在 _resolve_target 里发出。
            self._pending_resume_ms = resume_ms
            return
        self.backend.load(target)
        self._loaded_track_id = track.id
        if resume_ms > 0:
            self.backend.seek(resume_ms)
        self.backend.play()

    def play_track(self, track: Track) -> None:
        self.queue = [track]
        self.index = 0
        self.queueChanged.emit()
        self.play_index(0)

    def restore_state(self, tracks: list[Track], index: int, position_ms: int = 0,
                      autoplay: bool = False) -> None:
        """启动恢复：装回队列和当前曲目，本地文件只加载/定位，不默认出声。"""
        self._cancel_pending()
        self._play_token += 1
        self.queue = list(tracks)
        self.index = max(0, min(index, len(self.queue) - 1)) if self.queue else -1
        self.queueChanged.emit()
        track = self.current
        if track is None:
            self.stateChanged.emit("idle")
            return
        self.currentChanged.emit(track)
        if track.is_local and track.path and Path(track.path).exists():
            self._resume_track_id = None
            self._resume_position_ms = 0
            self._pending_resume_ms = 0
            self.backend.load_at(track.path, position_ms)
            self._loaded_track_id = track.id
            if autoplay:
                self.backend.play()
            else:
                self.backend.pause()
            return
        # 在线曲目只恢复元数据，不提前触发缓存/下载；点播放时再走正常解析。
        self._loaded_track_id = None
        self._resume_track_id = track.id
        self._resume_position_ms = max(0, int(position_ms))
        self.stateChanged.emit("paused")
        if autoplay:
            self.play_index(self.index)

    def toggle(self) -> None:
        if self.backend.is_playing():
            self.backend.pause()
        elif self.current is None and self.queue:
            self.play_index(max(0, self.index))
        elif self.current is not None and self._loaded_track_id != self.current.id:
            # 会话恢复的在线曲目只有元数据、后端没有源，先走正常解析。
            self.play_index(self.index)
        else:
            self.backend.play()

    def stop(self) -> None:
        self._cancel_pending()
        self.backend.stop()

    def next(self) -> None:
        if not self.queue:
            return
        if self.repeat == "one":
            self.backend.seek(0)
            self.backend.play()
            return
        if self.shuffle:
            self.play_index(random.randrange(len(self.queue)))
            return
        if self.index + 1 >= len(self.queue):
            if self.repeat == "all":
                self.play_index(0)
            else:
                self.backend.pause()
                self.backend.seek(0)
            return
        self.play_index(self.index + 1)

    def previous(self) -> None:
        if not self.queue:
            return
        self.play_index(max(0, self.index - 1))

    def set_repeat(self, mode: str) -> None:
        self.repeat = mode
        if self.settings:
            self.settings.set("repeat_mode", mode)

    def seek(self, position_ms: int) -> None:
        self.backend.seek(position_ms)

    def set_volume(self, volume: float) -> None:
        self.backend.set_volume(volume)
        if self.settings:
            self.settings.set("volume", round(float(volume), 2))

    # ---------------- 内部 ----------------
    def _resolve_target(self, track: Track, token: int) -> str:
        """解析播放目标。本地/完整缓存直接返回路径；在线歌曲登记缓存后等完整文件。"""
        if track.is_local:
            return track.path
        try:
            url = track.url or (self.adapter.resolve(track) if self.adapter else "")
            if not url:
                self.failed.emit(f"{track.display} 没有可用直链")
                return ""
            entry, _local = self.stream_cache.register(track)
            if entry.done:
                if not entry.final_path.exists():
                    self.failed.emit(f"{track.display} 缓存文件已丢失")
                    return ""
                problem = self._audio_problem(entry, track)
                if problem:
                    self._switch_or_fail(track, problem)
                    return ""
                return str(entry.final_path)
            if entry.error:
                self._switch_or_fail(track, f"{track.display} 缓存失败：{entry.error}")
                return ""
            # 不把 .part 交给播放器：等 entry.done 后由 _check_pending 播放完整文件。
            self._pending_entry = entry
            self._pending_token = token
            self._pending_since = time.monotonic()
            self._pending_timer.start()
            return ""
        except Exception as err:
            self.failed.emit(f"{track.display} 加载失败：{err}")
            return ""

    def _cancel_pending(self) -> None:
        """只取消“等待播放”的监听，不取消仍在后台下载的缓存。"""
        self._pending_timer.stop()
        self._pending_entry = None
        self._pending_token = -1

    def _check_pending(self) -> None:
        entry = self._pending_entry
        if entry is None or self._pending_token != self._play_token:
            self._cancel_pending()
            return
        track = self.current
        if entry.error:
            self._cancel_pending()
            if track:
                self._switch_or_fail(track, f"{track.display} 缓存失败：{entry.error}")
            return
        if entry.cancelled:
            self._cancel_pending()
            return
        if entry.done:
            path = entry.final_path
            self._cancel_pending()
            if not track:
                return
            if not path.exists():
                self._switch_or_fail(track, f"{track.display} 缓存文件已丢失")
                return
            problem = self._audio_problem(entry, track)
            if problem:
                self._switch_or_fail(track, problem)
                return
            self.backend.load(str(path))
            self._loaded_track_id = track.id
            if self._pending_resume_ms > 0:
                self.backend.seek(self._pending_resume_ms)
            self._pending_resume_ms = 0
            self.backend.play()
            return
        if time.monotonic() - self._pending_since > 180:
            self._cancel_pending()
            if track:
                self.failed.emit(f"{track.display} 缓存超时")

    def _audio_problem(self, entry, track: Track) -> str:
        """缓存文件是否完整。

        有些音源会返回约 30 秒的试听片段，或者服务端提前关闭但没给
        Content-Length；此时 entry.done 仍为 True。用 mutagen 读实际时长，
        明显短于搜索结果标注的时长就判定为残缺，交给备选源或明确提示。
        """
        expected = int(track.duration_ms or 0)
        if expected < 30_000:
            return ""
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(str(entry.final_path))
            info = getattr(audio, "info", None)
            actual = int(float(getattr(info, "length", 0) or 0) * 1000)
        except Exception:
            return ""
        if actual <= 0:
            return ""
        if actual < expected * 0.75:
            entry.error = f"音频时长异常：{actual // 1000}s / 预期 {expected // 1000}s"
            return f"{track.display} 音源只返回了约 {actual // 1000} 秒音频，疑似试听片段"

        # 有些 MP3 的 Xing/Info 头保留了完整时长，文件被截断后 mutagen
        # 仍会报告原时长；此时用“时长 × 实际码率”估算应有字节数。
        try:
            size = entry.final_path.stat().st_size
            bitrate = int(getattr(info, "bitrate", 0) or 0)
            expected_bytes = (expected / 1000.0) * (bitrate / 8.0) if bitrate > 0 else 0
            if expected_bytes > 0 and size < expected_bytes * 0.7:
                entry.error = f"文件疑似截断：{size} / {int(expected_bytes)} 字节"
                return (f"{track.display} 缓存文件只有 {size / 1048576:.1f} MB，"
                        f"按 {bitrate // 1000} kbps 应约 {expected_bytes / 1048576:.1f} MB，疑似截断")
        except Exception:
            pass
        return ""

    def _switch_or_fail(self, track: Track, message: str) -> bool:
        """优先切同曲的备选源；没有备选源时把错误抛给 UI。"""
        if track and track.alternatives:
            alt = track.alternatives.pop(0)
            alt.alternatives = track.alternatives
            self.queue[self.index] = alt
            self.failed.emit(f"{message}，切换备选源：{alt.source}")
            self.play_index(self.index)
            return True
        self.failed.emit(message)
        return False

    def _on_end(self) -> None:
        self.next()

    def _on_error(self, message: str) -> None:
        track = self.current
        if track:
            self._switch_or_fail(track, message)
        else:
            self.failed.emit(message)
