"""收藏页：显示用户收藏的歌曲，支持取消收藏与快速入队。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMenu, QVBoxLayout, QWidget

from shiyin.app.ui.models.track_model import TrackTableModel
from shiyin.app.ui.widgets.page_header import PageHeader
from shiyin.app.ui.widgets.track_list import TrackListView, style_track_list


class FavoritesPage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._model = TrackTableModel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        self.header = PageHeader("我的收藏")
        self.header.add_action("取消收藏", self.unfavorite_selected)
        self.header.add_action("播放全部", self.play_all, primary=True)
        layout.addWidget(self.header)

        self.hint = QLabel("")
        self.hint.setObjectName("hintLabel")
        self.hint.setVisible(False)
        layout.addWidget(self.hint)

        self.list = TrackListView()
        self.list.setModel(self._model)
        style_track_list(self.list, "还没有收藏的歌曲\n在搜索或本地库右键「收藏」即可加入")
        self.list.doubleClicked.connect(self.play_selected)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list, 1)

        self.reload()

    # ---------------- 数据 ----------------
    def reload(self) -> None:
        """重新加载收藏列表"""
        tracks = self.context.repository.playlist_tracks("favorites")
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
        """播放选中的歌曲"""
        track = self._selected()
        if track:
            self.context.playback.play_track(track)

    def play_all(self) -> None:
        """播放所有收藏歌曲"""
        tracks = [self._model.track(row) for row in range(self._model.rowCount())]
        tracks = [t for t in tracks if t]
        if tracks:
            self.context.playback.set_queue(tracks, 0)

    def unfavorite_selected(self) -> None:
        track = self._selected()
        if not track:
            self._set_hint("先选中一首歌")
            return
        self._unfavorite(track)

    def _unfavorite(self, track) -> None:
        self.context.repository.remove_from_playlist("favorites", track.id)
        self.reload()
        self._set_hint(f"已取消收藏：{track.display}")

    def _on_context_menu(self, pos) -> None:
        # 右键先选中该行，否则会误操作上一次选中的歌
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
        menu.addAction("加入歌单…", lambda: self._add_to_playlist(track))
        menu.addAction("取消收藏", lambda: self._unfavorite(track))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _add_to_playlist(self, track) -> None:
        from shiyin.app.ui.dialogs.playlist_picker import add_track

        message = add_track(self, self.context.repository, track)
        if message:
            self._set_hint(message)
