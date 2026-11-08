"""搜索页：多源聚合结果、试听、下载、加入队列。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QVBoxLayout, QWidget

from shiyin.app.adapters import source_catalog
from shiyin.app.core.models import SearchResult, Track
from shiyin.app.ui.models.track_model import TrackTableModel
from shiyin.app.ui.widgets.page_header import PageHeader
from shiyin.app.ui.widgets.track_list import TrackListView, style_track_list


class SearchWorker(QThread):
    resultReady = Signal(object)
    partialReady = Signal(object, object, int, int)  # items, errors, done, total

    def __init__(self, service, keyword: str, sources: list[str], parent=None):
        super().__init__(parent)
        self._service = service
        self._keyword = keyword
        self._sources = sources

    def run(self) -> None:
        try:
            result = self._service.search(self._keyword, self._sources, on_partial=self._on_partial)
        except Exception as err:
            result = SearchResult(keyword=self._keyword, errors={"全部": f"{type(err).__name__}: {err}"})
        self.resultReady.emit(result)

    def _on_partial(self, items, errors, done: int, total: int) -> None:
        self.partialReady.emit(items, errors, done, total)


class SearchPage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._worker: SearchWorker | None = None
        self._errors: dict[str, str] = {}
        self._model = TrackTableModel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        self.header = PageHeader("搜索")
        self.error_btn = QPushButton("")
        self.error_btn.setObjectName("linkButton")
        self.error_btn.setVisible(False)
        self.error_btn.clicked.connect(self._show_errors)
        self.header.add_widget(self.error_btn)
        layout.addWidget(self.header)

        self.hint = QLabel("")
        self.hint.setObjectName("hintLabel")
        self.hint.setVisible(False)
        layout.addWidget(self.hint)

        self.list = TrackListView()
        self.list.setModel(self._model)
        style_track_list(self.list, "输入关键词开始搜索\n支持多音源聚合，边搜边出结果")
        self.list.doubleClicked.connect(self._on_double_click)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list, 1)

    def _set_hint(self, text: str) -> None:
        self.hint.setText(text)
        self.hint.setVisible(bool(text))

    # ---------------- 搜索 ----------------
    def search(self, keyword: str) -> None:
        """从主窗口搜索框调用，更新标题并开始搜索"""
        if not keyword:
            self.header.set_title("搜索")
            self.header.set_subtitle("请输入关键词")
            return
        self.header.set_title(f"搜索「{keyword}」")
        self.header.set_subtitle("正在搜索…")
        self._set_hint("")
        self._clear_errors()
        self._start_search(keyword)

    def _start_search(self, keyword: str) -> None:
        if self._worker and self._worker.isRunning():
            return
        sources = self.context.settings.enabled_sources
        self._model.set_tracks([])
        self._worker = SearchWorker(self.context.search, keyword, sources, self)
        self._worker.partialReady.connect(self._on_partial)
        self._worker.resultReady.connect(self._on_result)
        self._worker.start()

    def _on_partial(self, items, errors, done: int, total: int) -> None:
        """先落定的源先上屏：用户几秒内就能看到结果，不必等满超时。"""
        if items:
            self._model.set_tracks(items)
        text = f"搜索中 {done}/{total} 个源 · 已找到 {len(items)} 首"
        if errors:
            text += f" · {len(errors)} 个源暂无结果"
        self.header.set_subtitle(text)

    def _on_result(self, result: SearchResult) -> None:
        self._model.set_tracks(result.items)
        self._errors = dict(result.errors or {})

        text = f"共 {len(result.items)} 条 · 用时 {result.elapsed_ms} ms"
        if not result.items:
            text += " · 换个关键词，或到设置页检测/换源试试"
        self.header.set_subtitle(text)

        if self._errors:
            self.error_btn.setText(f"{len(self._errors)} 个源未响应 ▾")
            names = "、".join(source_catalog.source_label(k) for k in list(self._errors)[:4])
            self.error_btn.setToolTip(f"未响应：{names}")
            self.error_btn.setVisible(True)
        else:
            self.error_btn.setVisible(False)

    def _clear_errors(self) -> None:
        self._errors = {}
        self.error_btn.setVisible(False)

    def _show_errors(self) -> None:
        if not self._errors:
            return
        menu = QMenu(self)
        for source, message in self._errors.items():
            label = source_catalog.source_label(source)
            action = menu.addAction(f"{label}：{message or '无结果'}")
            action.setEnabled(False)
        menu.exec(self.error_btn.mapToGlobal(self.error_btn.rect().bottomLeft()))

    # ---------------- 操作 ----------------
    def _selected_track(self) -> Track | None:
        rows = self.list.selected_rows()
        if not rows:
            return None
        return self._model.track(rows[0])

    def _on_double_click(self, index) -> None:
        track = self._model.track(index.row())
        if track:
            self.context.playback.play_track(track)

    def _on_context_menu(self, pos) -> None:
        index = self.list.indexAt(pos)
        if not index.isValid():
            return
        self.list.select_row(index.row())
        track = self._model.track(index.row())
        if not track:
            return

        menu = QMenu(self)
        favorite = self.context.repository.is_in_playlist("favorites", track.id)
        fav_action = menu.addAction("取消收藏" if favorite else "收藏")
        if favorite:
            fav_action.triggered.connect(lambda: self._on_unfavorite(track))
        else:
            fav_action.triggered.connect(lambda: self._on_favorite(track))
        menu.addAction("下载", lambda: self._on_download(track))
        menu.addAction("加入队列", lambda: self._on_enqueue(track))
        menu.addAction("加入歌单…", lambda: self._on_add_to_playlist(track))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _on_favorite(self, track: Track) -> None:
        self.context.repository.add_to_playlist("favorites", track)
        self._set_hint(f"已收藏：{track.display}")

    def _on_unfavorite(self, track: Track) -> None:
        self.context.repository.remove_from_playlist("favorites", track.id)
        self._set_hint(f"已取消收藏：{track.display}")

    def _on_add_to_playlist(self, track: Track) -> None:
        from shiyin.app.ui.dialogs.playlist_picker import add_track

        message = add_track(self, self.context.repository, track)
        if message:
            self._set_hint(message)

    def _on_download(self, track: Track) -> None:
        self.context.downloads.submit(track)
        self._set_hint(f"已加入下载队列：{track.display}")

    def _on_enqueue(self, track: Track) -> None:
        self.context.playback.enqueue(track)
        self._set_hint(f"已加入播放列表：{track.display}")
