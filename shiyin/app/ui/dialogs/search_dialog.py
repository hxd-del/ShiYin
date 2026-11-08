"""搜索对话框：独立弹出的多源聚合搜索窗口。"""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QHBoxLayout, QLabel,
                               QPushButton, QTableView, QVBoxLayout)

from shiyin.app.adapters import source_catalog
from shiyin.app.core.models import SearchResult, Track
from shiyin.app.ui.models.track_model import TrackTableModel


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


class SearchDialog(QDialog):
    def __init__(self, context, keyword: str = "", parent=None):
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("搜索结果")
        self.resize(900, 600)
        self._worker: SearchWorker | None = None
        self._model = TrackTableModel()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 12)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.keyword_label = QLabel(f"搜索：{keyword}")
        self.keyword_label.setObjectName("sectionTitle")
        self.source_label = QLabel("")
        self.source_label.setObjectName("hintLabel")
        self.merge_box = QCheckBox("合并同曲")
        self.merge_box.setToolTip("关闭时同一首歌在各音源分别列出，条数更多；打开后只保留音质最高的一条")
        self.merge_box.setChecked(bool(self.context.settings.get("merge_same_song")))
        self.merge_box.toggled.connect(self._on_merge_toggled)
        top.addWidget(self.keyword_label, 1)
        top.addWidget(self.merge_box)
        top.addWidget(self.source_label)
        layout.addLayout(top)

        self.table = QTableView()
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(0, 300)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 180)
        self.table.doubleClicked.connect(lambda _: self.play_selected())
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.status = QLabel("搜索中…")
        self.status.setObjectName("hintLabel")
        bottom.addWidget(self.status, 1)
        for text, handler in [
            ("试听", self.play_selected),
            ("下载", self.download_selected),
            ("加入队列", self.enqueue_selected),
            ("收藏", self.favorite_selected),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("ghostButton")
            btn.clicked.connect(handler)
            bottom.addWidget(btn)
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

        self.start_search(keyword)

    # ---------------- 搜索 ----------------
    def _on_merge_toggled(self, checked: bool) -> None:
        self.context.search.merge_same_song = checked
        self.context.settings.set("merge_same_song", checked)
        self.status.setText("已切换为合并同曲，重新搜索后生效" if checked else "已切换为分源列出，重新搜索后生效")

    def start_search(self, keyword: str) -> None:
        if not keyword:
            self.status.setText("请输入关键词")
            return
        if self._worker and self._worker.isRunning():
            return
        sources = self.context.settings.enabled_sources
        self.source_label.setText(f"启用 {len(sources)} 个音源")
        self.status.setText(f"正在搜索「{keyword}」…")
        self._model.set_tracks([])
        self._worker = SearchWorker(self.context.search, keyword, sources, self)
        self._worker.partialReady.connect(self._on_partial)
        self._worker.resultReady.connect(self._on_result)
        self._worker.start()

    def _on_partial(self, items, errors, done: int, total: int) -> None:
        """先落定的源先上屏：用户几秒内就能看到结果，不必等满超时。"""
        if items:
            self._model.set_tracks(items)
        text = f"搜索中 {done}/{total} 个源，已找到 {len(items)} 首"
        if errors:
            text += f"，{len(errors)} 个源暂无结果"
        self.status.setText(text)

    def _on_result(self, result: SearchResult) -> None:
        self._model.set_tracks(result.items)
        text = f"{result.summary}，用时 {result.elapsed_ms} ms"
        if result.errors:
            names = "、".join(source_catalog.source_label(k) for k in list(result.errors)[:4])
            text += f"；{len(result.errors)} 个源未响应（{names}），可在设置页「检测音源」筛掉它们"
        if not result.items:
            text += "。换个关键词，或到设置页检测/换源试试"
        self.status.setText(text)

    # ---------------- 操作 ----------------
    def _selected(self) -> Track | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.status.setText("先在列表里选中一首歌")
            return None
        return self._model.track(rows[0].row())

    def play_selected(self) -> None:
        track = self._selected()
        if track:
            self.context.playback.play_track(track)
            self.status.setText(f"试听：{track.display}")

    def download_selected(self) -> None:
        track = self._selected()
        if track:
            task_id = self.context.downloads.submit(track)
            self.status.setText(f"已加入下载队列：{track.display}（{task_id}）")

    def enqueue_selected(self) -> None:
        track = self._selected()
        if track:
            self.context.playback.enqueue(track)
            self.status.setText(f"已加入队列：{track.display}")

    def favorite_selected(self) -> None:
        track = self._selected()
        if track:
            self.context.repository.add_to_playlist("favorites", track)
            self.status.setText(f"已收藏：{track.display}")
