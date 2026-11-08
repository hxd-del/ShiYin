"""播放栏的缓冲转圈：套在播放键外侧的一圈旋转弧线。

为什么不用文字或静态图标：在线试听从登记缓存到真正出声之间有一段等待，
Qt 的 loading/buffering 状态没有可见反馈时，用户会以为点了没反应。
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class BufferSpinner(QWidget):
    """透明、不接收鼠标事件的旋转弧线，作为一个覆盖层放在播放键上。"""

    def __init__(self, parent=None, size: int = 44, color: str = "#2ecb71"):
        super().__init__(parent)
        self._color = QColor(color)
        self._angle = 0
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._advance)
        self.hide()

    def start(self) -> None:
        self._angle = 0
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self.hide()

    def _advance(self) -> None:
        self._angle = (self._angle + 12) % 360
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 命名
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(self._color, 3)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(QRectF(5, 5, self.width() - 10, self.height() - 10),
                        self._angle * 16, 300 * 16)
        painter.end()
