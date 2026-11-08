"""歌曲列表项：类似网易云音乐的歌曲行样式。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget)

from shiyin.app.core.models import Track


class TrackRowWidget(QWidget):
    """单个歌曲行组件"""
    play_clicked = Signal(object)  # 播放
    favorite_clicked = Signal(object)  # 收藏
    download_clicked = Signal(object)  # 下载
    enqueue_clicked = Signal(object)  # 加入队列

    def __init__(self, track: Track, index: int, parent=None):
        super().__init__(parent)
        self.track = track
        self.index = index
        self._setup_ui()

    def _setup_ui(self) -> None:
        # 使用垂直布局，包含内容行和分割线
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 内容行
        row_widget = QWidget()
        layout = QHBoxLayout(row_widget)
        layout.setContentsMargins(12, 4, 12, 4)  # 减少上下边距
        layout.setSpacing(12)

        # 序号
        index_label = QLabel(str(self.index + 1))
        index_label.setFixedWidth(30)
        index_label.setAlignment(Qt.AlignCenter)
        index_label.setObjectName("trackIndex")
        layout.addWidget(index_label)

        # 歌曲信息（歌名 + 歌手）
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)  # 减少间距
        info_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(self.track.title)
        title_label.setObjectName("trackTitle")
        title_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        info_layout.addWidget(title_label)

        artist_label = QLabel(self.track.artist)
        artist_label.setObjectName("trackArtist")
        artist_label.setStyleSheet("color: #888; font-size: 12px;")
        info_layout.addWidget(artist_label)

        info_widget = QWidget()
        info_widget.setLayout(info_layout)
        layout.addWidget(info_widget, 1)

        # 操作按钮（放在中间）
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        # 收藏按钮
        fav_btn = QPushButton("♡")
        fav_btn.setObjectName("trackFavBtn")
        fav_btn.setToolTip("收藏")
        fav_btn.setFixedSize(24, 24)  # 缩小按钮
        fav_btn.setStyleSheet("border: none; background: transparent;")
        fav_btn.clicked.connect(lambda: self.favorite_clicked.emit(self.track))
        btn_layout.addWidget(fav_btn)

        # 下载按钮
        dl_btn = QPushButton("↓")
        dl_btn.setObjectName("trackDlBtn")
        dl_btn.setToolTip("下载")
        dl_btn.setFixedSize(24, 24)  # 缩小按钮
        dl_btn.setStyleSheet("border: none; background: transparent;")
        dl_btn.clicked.connect(lambda: self.download_clicked.emit(self.track))
        btn_layout.addWidget(dl_btn)

        btn_widget = QWidget()
        btn_widget.setLayout(btn_layout)
        btn_widget.setFixedWidth(60)
        layout.addWidget(btn_widget)

        # 专辑
        album_label = QLabel(self.track.album or "--")
        album_label.setObjectName("trackAlbum")
        album_label.setStyleSheet("color: #666; font-size: 12px;")
        album_label.setMaximumWidth(200)
        layout.addWidget(album_label)

        # 时长
        duration_label = QLabel(self._format_duration())
        duration_label.setObjectName("trackDuration")
        duration_label.setStyleSheet("color: #888; font-size: 12px;")
        duration_label.setFixedWidth(60)
        duration_label.setAlignment(Qt.AlignRight)
        layout.addWidget(duration_label)

        outer_layout.addWidget(row_widget)

        # 添加底部分割线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("background-color: #e8e8e8; border: none; max-height: 1px;")
        outer_layout.addWidget(line)

        # 悬停效果
        self.setStyleSheet("""
            TrackRowWidget:hover {
                background-color: #f5f5f5;
            }
        """)

    def _format_duration(self) -> str:
        if not self.track.duration_ms:
            return "--:--"
        total_seconds = self.track.duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
