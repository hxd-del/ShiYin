"""可点击跳转的滑块。

原生 QSlider 点击轨道只按 pageStep 翻页，用户想直接点到某处时必须先瞄准手柄。
这里把按下与拖动都换算成绝对位置，音量与播放进度都能"点哪跳哪"。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSlider

from shiyin.app.ui.widgets.slider_math import value_at as _value_at


class ClickSlider(QSlider):
    HANDLE_MARGIN = 7  # 手柄半径；两端留白，保证 0 和最大值都点得到

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def value_at(self, x: float) -> int:
        return _value_at(x, self.minimum(), self.maximum(), self.width(), self.HANDLE_MARGIN)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.maximum() > self.minimum():
            # setSliderDown 会自动发出 sliderPressed / sliderReleased，
            # 播放进度条正是靠这两个信号区分"拖动中"和"松手后 seek"。
            self.setSliderDown(True)
            self.setValue(self.value_at(event.position().x()))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isSliderDown() and self.maximum() > self.minimum():
            self.setValue(self.value_at(event.position().x()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.isSliderDown():
            self.setValue(self.value_at(event.position().x()))
            self.setSliderDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)
