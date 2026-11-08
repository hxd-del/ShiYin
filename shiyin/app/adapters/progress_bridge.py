"""进度桥：把服务层的快照轮询成 Qt 信号。

上游的 rich 进度条在后台线程里跑，界面不能直接读；统一按 200 ms 节流，
避免十个源同时刷新把主线程压满。
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal


class ProgressBridge(QObject):
    updated = Signal(object)

    def __init__(self, snapshot: Callable[[], object], interval_ms: int = 200, parent=None):
        super().__init__(parent)
        self._snapshot = snapshot
        self._timer = QTimer(self)
        self._timer.setInterval(max(50, interval_ms))
        self._timer.timeout.connect(self._emit)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _emit(self) -> None:
        try:
            payload = self._snapshot()
        except Exception:
            return
        self.updated.emit(payload)
