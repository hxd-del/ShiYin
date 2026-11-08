"""最近播放页：按时间倒序显示最近听过的歌。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMenu, QVBoxLayout, QWidget

from shiyin.app.ui.models.track_model import TrackTableModel
from shiyin.app.ui.widgets.page_header import PageHeader
from shiyin.app.ui.widgets.track_list import TrackListView, style_track_list


class RecentPage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._model = TrackTableModel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        self.header = PageHeader("最近播放")
        self.header.add_action("清空记录", self.clear_recent)
        self.header.add_action("播放全部", self.play_all, primary=True)
        layout.addWidget(self.header)

        self.hint = QLabel("")
        self.hint.setObjectName("hintLabel")
        self.hint.setVisible(False)
        layout.addWidget(self.hint)

        self.list = TrackListView()
        self.list.setModel(self._model)
        style_track_list(self.list, "还没有播放记录\n播放任意一首歌后会自动记录")
        self.list.doubleClicked.connect(self.play_selected)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list, 1)

        self.reload()

    # ---------------- 数据 ----------------
    def reload(self) -> None:
        """最新的在最上面；同一首歌只留一条（再播一次会顶到最前）。"""
        tracks = self.context.repository.playlist_tracks("recent", newest_first=True)
        self._model.set_tracks(tracks)
        self.header.set_subtitle(f"{len(tracks)} 首")
        self._set_hint("")

    def _set_hint(self, text: str) -> None:
        self.hint.setText(text)
        self.hint.setVisible(bool(text))

    def _selected(self):
        rows = self.list.selected_rows()
        if not rows:
            return None
        return self._model.track(rows[0])

    # ---------------- 操作 ----------------
    def play_selected(self, *_args) -> None:
        track = self._selected()
        if track:
            self.context.playback.play_track(track)

    def play_all(self) -> None:
        tracks = [self._model.track(row) for row in range(self._model.rowCount())]
        tracks = [t for t in tracks if t]
        if tracks:
            self.context.playback.set_queue(tracks, 0)

    def clear_recent(self) -> None:
        self.context.repository.clear_playlist("recent")
        self.reload()
        self._set_hint("已清空最近播放记录")

    def _on_context_menu(self, pos) -> None:
        index = self.list.indexAt(pos)
        if not index.isValid():
            return
        self.list.select_row(index.row())
        track = self._model.track(index.row())
        if not track:
            return
        menu = QMenu(self)
        menu.addAction("播放", lambda: self.context.playback.play_track(track))
        menu.addAction("加入队列", lambda: self.context.playback.enqueue(track))
        menu.addAction("收藏", lambda: self._favorite(track))
        menu.addAction("从记录中移除", lambda: self._remove(track))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _favorite(self, track) -> None:
        self.context.repository.add_to_playlist("favorites", track)
        self._set_hint(f"已收藏：{track.display}")

    def _remove(self, track) -> None:
        self.context.repository.remove_from_playlist("recent", track.id)
        self.reload()
        self._set_hint(f"已从最近播放移除：{track.display}")
