"""音频后端：把播放器能力收敛成一个小接口。

默认实现基于 Qt Multimedia；未来要换 libmpv 只需在这里加一个实现类。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AudioBackend(QObject):
    positionChanged = Signal(int)
    durationChanged = Signal(int)
    stateChanged = Signal(str)
    errorOccurred = Signal(str)
    endReached = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._output = QAudioOutput(self)
        self._player.setAudioOutput(self._output)
        self._state = "idle"
        self._restore_position = -1
        self._player.positionChanged.connect(self.positionChanged.emit)
        self._player.durationChanged.connect(self.durationChanged.emit)
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.errorOccurred.connect(self._on_error)

    # ---------------- 能力 ----------------
    def load(self, target: str) -> None:
        self._restore_position = -1
        self._set_state("loading")
        # 先停止当前播放，确保播放器状态干净
        self._player.stop()
        url = QUrl(target) if "://" in target else QUrl.fromLocalFile(target)
        self._player.setSource(url)

    def load_at(self, target: str, position_ms: int) -> None:
        """加载后停在指定位置：等媒体真正 Loaded 再 seek，避免 setSource 后立即
        setPosition 被 Qt 丢掉。"""
        self.load(target)
        self._restore_position = max(0, int(position_ms))

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def seek(self, position_ms: int) -> None:
        self._player.setPosition(max(0, int(position_ms)))

    def set_volume(self, value: float) -> None:
        self._output.setVolume(max(0.0, min(1.0, float(value))))

    def set_rate(self, rate: float) -> None:
        self._player.setPlaybackRate(max(0.5, min(3.0, float(rate))))

    def position(self) -> int:
        return int(self._player.position())

    def duration(self) -> int:
        return int(self._player.duration())

    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # ---------------- 信号转译 ----------------
    def _set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            self.stateChanged.emit(state)

    def _on_state(self, state) -> None:
        mapping = {
            QMediaPlayer.PlaybackState.PlayingState: "playing",
            QMediaPlayer.PlaybackState.PausedState: "paused",
            QMediaPlayer.PlaybackState.StoppedState: "idle",
        }
        self._set_state(mapping.get(state, "idle"))

    def _on_status(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._set_state("idle")
            self.endReached.emit()
        elif status in (QMediaPlayer.MediaStatus.LoadedMedia,
                        QMediaPlayer.MediaStatus.BufferedMedia):
            if self._restore_position >= 0:
                self._player.setPosition(self._restore_position)
                self._restore_position = -1
                # setSource 后 Qt 的 playbackState 仍是 Stopped，不会自动发 paused；
                # 会话恢复需要把内部状态标成暂停，按钮才不会停在加载态。
                self._set_state("paused")
        elif status in (QMediaPlayer.MediaStatus.BufferingMedia,
                        QMediaPlayer.MediaStatus.StalledMedia):
            # 已经出声时媒体状态仍可能短暂进入 Buffering/Stalled，但播放状态还是
            # Playing。此时若把内部状态改成 buffering，界面会把播放键画成“播放”，
            # 直到用户点一次才恢复。只有真正未在播放时才上报 buffering。
            if (self._player.playbackState()
                    != QMediaPlayer.PlaybackState.PlayingState):
                self._set_state("buffering")

    def _on_error(self, error, message: str = "") -> None:
        if error == QMediaPlayer.Error.NoError:
            return
        self._set_state("failed")
        self.errorOccurred.emit(message or "播放器错误")


class MpvAudioBackend(AudioBackend):
    """占位实现：接入 python-mpv 时替换掉父类内部实现即可，接口保持一致。"""
