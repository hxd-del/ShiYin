"""播放列表页：查看当前队列、双击切歌、移除单首或清空。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu, QVBoxLayout, QWidget
from PySide6.QtWidgets import QAbstractItemView

from shiyin.app.ui.models.track_model import TrackTableModel
from shiyin.app.ui.widgets.page_header import PageHeader
from shiyin.app.ui.widgets.track_list import TrackListView, style_track_list


class QueuePage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.playback = context.playback
        self._model = TrackTableModel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        self.header = PageHeader("正在播放")
        self.header.add_action("移除选中", self.remove_selected)
        self.header.add_action("清空列表", self.clear_queue)
        layout.addWidget(self.header)

        self.list = TrackListView()
        self.list.setModel(self._model)
        style_track_list(self.list, "播放列表为空\n在歌曲上右键「加入队列」或双击歌曲开始播放")
        self.list.doubleClicked.connect(self._play_row)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list, 1)

        self.playback.queueChanged.connect(self.reload)
        self.playback.currentChanged.connect(self._on_current_changed)
        self.reload()

    # ---------------- 数据 ----------------
    def reload(self) -> None:
        self._model.set_tracks(list(self.playback.queue))
        self._sync_selection()

    def _sync_selection(self) -> None:
        index = self.playback.index
        count = self._model.rowCount()
        if 0 <= index < count:
            self.list.select_row(index)
            self.list.scrollTo(self._model.index(index, 0), QAbstractItemView.PositionAtCenter)
            self.header.set_subtitle(f"队列 {count} 首 · 第 {index + 1} 首 · 双击切歌")
        else:
            self.list.clearSelection()
            self.header.set_subtitle(f"队列 {count} 首 · 双击切歌" if count else "队列为空")

    def _on_current_changed(self, _track) -> None:
        self._sync_selection()

    # ---------------- 操作 ----------------
    def _play_row(self, index) -> None:
        row = index.row() if hasattr(index, "row") else int(index)
        if 0 <= row < len(self.playback.queue):
            self.playback.play_index(row)

    def remove_selected(self) -> None:
        rows = self.list.selected_rows()
        if not rows:
            return
        self.playback.remove_at(rows[0])

    def clear_queue(self) -> None:
        self.playback.clear_queue()

    def _on_context_menu(self, pos) -> None:
        index = self.list.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        self.list.select_row(row)
        track = self._model.track(row)
        if track is None:
            return
        menu = QMenu(self)
        menu.addAction("播放", lambda: self.playback.play_index(row))
        menu.addAction("加入歌单…", lambda: self._add_to_playlist(track))
        menu.addAction("从列表移除", lambda: self.playback.remove_at(row))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _add_to_playlist(self, track) -> None:
        from shiyin.app.ui.dialogs.playlist_picker import add_track

        add_track(self, self.context.repository, track)
