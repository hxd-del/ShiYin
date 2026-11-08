"""歌单页：收藏、最近播放与自建歌单的浏览、编辑与播放。"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QMenu, QPushButton, QVBoxLayout, QWidget)

from shiyin.app.ui.models.track_model import TrackTableModel
from shiyin.app.ui.widgets.page_header import PageHeader
from shiyin.app.ui.widgets.track_list import TrackListView, style_track_list

_ID_ROLE = 0x0100


class PlaylistsPage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._model = TrackTableModel()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(14)

        # 左侧歌单面板
        panel = QFrame()
        panel.setObjectName("sidePanel")
        panel.setFixedWidth(240)
        left = QVBoxLayout(panel)
        left.setContentsMargins(12, 12, 12, 12)
        left.setSpacing(8)
        title = QLabel("歌单")
        title.setObjectName("cardTitle")
        left.addWidget(title)
        self.playlists = QListWidget()
        self.playlists.setObjectName("playlistList")
        self.playlists.setFrameShape(QFrame.NoFrame)
        self.playlists.currentItemChanged.connect(self._load_playlist)
        left.addWidget(self.playlists, 1)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.new_btn = QPushButton("新建")
        self.new_btn.setObjectName("panelButton")
        self.new_btn.clicked.connect(self.create_playlist)
        row.addWidget(self.new_btn)
        self.rename_btn = QPushButton("重命名")
        self.rename_btn.setObjectName("panelButton")
        self.rename_btn.clicked.connect(self.rename_playlist)
        row.addWidget(self.rename_btn)
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setObjectName("panelButton")
        self.delete_btn.clicked.connect(self.delete_playlist)
        row.addWidget(self.delete_btn)
        left.addLayout(row)
        layout.addWidget(panel)

        # 右侧曲目
        right = QVBoxLayout()
        right.setSpacing(10)
        self.header = PageHeader("我的收藏")
        self.header.add_action("播放歌单", self.play_all, primary=True)
        right.addWidget(self.header)
        self.hint = QLabel("")
        self.hint.setObjectName("hintLabel")
        self.hint.setVisible(False)
        right.addWidget(self.hint)
        self.list = TrackListView()
        self.list.setModel(self._model)
        style_track_list(self.list, "这个歌单还是空的\n在歌曲上右键「加入歌单」即可添加")
        self.list.doubleClicked.connect(self.play_selected)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        right.addWidget(self.list, 1)
        layout.addLayout(right, 1)

        self.reload()

    # ---------------- 数据 ----------------
    def reload(self) -> None:
        current = self._current_id()
        self.playlists.clear()
        for playlist in self.context.repository.list_playlists():
            item = QListWidgetItem(f"{playlist['name']}（{playlist['count']}）")
            item.setData(_ID_ROLE, playlist["id"])
            item.setSizeHint(QSize(0, 38))
            self.playlists.addItem(item)
            if playlist["id"] == current:
                self.playlists.setCurrentItem(item)
        if self.playlists.currentRow() < 0 and self.playlists.count():
            self.playlists.setCurrentRow(0)
        self._update_edit_buttons()

    def _current_id(self) -> str | None:
        item = self.playlists.currentItem()
        return item.data(_ID_ROLE) if item else None

    def _current_kind(self) -> str:
        playlist_id = self._current_id()
        for playlist in self.context.repository.list_playlists():
            if playlist["id"] == playlist_id:
                return playlist["kind"]
        return ""

    def _update_edit_buttons(self) -> None:
        is_user = self._current_kind() == "user"
        self.rename_btn.setEnabled(is_user)
        self.delete_btn.setEnabled(is_user)

    def _load_playlist(self, *_args) -> None:
        playlist_id = self._current_id()
        if not playlist_id:
            return
        tracks = self.context.repository.playlist_tracks(playlist_id)
        self._model.set_tracks(tracks)
        item = self.playlists.currentItem()
        name = item.text().rsplit("（", 1)[0] if item else "歌单"
        self.header.set_title(name)
        self.header.set_subtitle(f"{len(tracks)} 首")
        self._set_hint("")
        self._update_edit_buttons()

    def _set_hint(self, text: str) -> None:
        self.hint.setText(text)
        self.hint.setVisible(bool(text))

    # ---------------- 歌单管理 ----------------
    def create_playlist(self) -> None:
        name, ok = QInputDialog.getText(self, "新建歌单", "名称：")
        if ok and name.strip():
            self.context.repository.create_playlist(name.strip())
            self.reload()
            self._set_hint(f"已新建歌单：{name.strip()}")

    def rename_playlist(self) -> None:
        playlist_id = self._current_id()
        if not playlist_id or self._current_kind() != "user":
            return
        name, ok = QInputDialog.getText(self, "重命名歌单", "新名称：")
        if ok and name.strip():
            self.context.repository.rename_playlist(playlist_id, name.strip())
            self.reload()
            self._set_hint(f"已重命名为：{name.strip()}")

    def delete_playlist(self) -> None:
        playlist_id = self._current_id()
        if not playlist_id or self._current_kind() != "user":
            self._set_hint("内置列表不能删除")
            return
        ok = self.context.repository.delete_playlist(playlist_id)
        if ok:
            self.reload()
            self._set_hint("歌单已删除")

    # ---------------- 曲目操作 ----------------
    def _selected(self):
        rows = self.list.selected_rows()
        if not rows:
            return None
        return self._model.track(rows[0])

    def play_selected(self, *_args) -> None:
        track = self._selected()
        if track:
            self.context.playback.play_track(track)

    def play_all(self) -> None:
        tracks = [self._model.track(row) for row in range(self._model.rowCount())]
        tracks = [t for t in tracks if t]
        if tracks:
            self.context.playback.set_queue(tracks, 0)

    def _on_context_menu(self, pos) -> None:
        index = self.list.indexAt(pos)
        if not index.isValid():
            return
        self.list.select_row(index.row())
        track = self._model.track(index.row())
        playlist_id = self._current_id()
        if not track or not playlist_id:
            return
        menu = QMenu(self)
        menu.addAction("播放", lambda: self.context.playback.play_track(track))
        menu.addAction("加入队列", lambda: self.context.playback.enqueue(track))
        menu.addAction("加入其他歌单…", lambda: self._add_to_other(track))
        menu.addAction("从本歌单移除", lambda: self._remove_track(track, playlist_id))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _add_to_other(self, track) -> None:
        from shiyin.app.ui.dialogs.playlist_picker import add_track

        message = add_track(self, self.context.repository, track)
        if message:
            self._set_hint(message)

    def _remove_track(self, track, playlist_id: str) -> None:
        self.context.repository.remove_from_playlist(playlist_id, track.id)
        self._load_playlist()
        self.reload()
        self._set_hint(f"已移除：{track.display}")
