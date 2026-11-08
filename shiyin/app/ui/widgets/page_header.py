"""统一页头：标题 + 副标题 + 右侧操作按钮（第二批 P2-1）。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class PageHeader(QWidget):
    """页面顶部：大标题 + 灰色副标题，右侧放操作按钮。"""

    def __init__(self, title: str = "", subtitle: str = "", parent=None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        text = QVBoxLayout()
        text.setContentsMargins(0, 0, 0, 0)
        text.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("pageSubtitle")
        self.subtitle_label.setVisible(bool(subtitle))
        text.addWidget(self.title_label)
        text.addWidget(self.subtitle_label)
        root.addLayout(text, 1)

        self.actions = QHBoxLayout()
        self.actions.setContentsMargins(0, 0, 0, 0)
        self.actions.setSpacing(8)
        self.actions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        root.addLayout(self.actions)

    # ---------------- 文本 ----------------
    def set_title(self, text: str) -> None:
        self.title_label.setText(text)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))

    def text(self) -> str:
        """兼容旧代码里直接取文本的写法。"""
        return self.title_label.text()

    # ---------------- 操作区 ----------------
    def add_action(self, text: str, slot=None, primary: bool = False) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("primaryButton" if primary else "ghostButton")
        if slot is not None:
            button.clicked.connect(slot)
        self.actions.addWidget(button)
        return button

    def add_widget(self, widget: QWidget) -> None:
        self.actions.addWidget(widget)
