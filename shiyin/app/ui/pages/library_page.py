"""本地库页：扫描目录、检索、双击播放。"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMenu, QVBoxLayout,
                               QWidget)

from shiyin.app.data.repository import Repository
from shiyin.app.services.library_service import LibraryService
from shiyin.app.ui.models.track_model import TrackTableModel
from shiyin.app.ui.widgets.page_header import PageHeader
from shiyin.app.ui.widgets.track_list import TrackListView, style_track_list


class ScanWorker(QThread):
    finishedScan = Signal(object)

    def __init__(self, library, directory: str, parent=None):
        super().__init__(parent)
        self._library = library
        self._directory = directory

    def run(self) -> None:
        self.finishedScan.emit(self._library.scan(self._directory))


class StartupScanWorker(QThread):
    """启动扫描：独立 SQLite 连接，避免和主线程收藏/播放写库抢锁。"""

    progress = Signal(int, int, str)
    finishedScan = Signal(object)

    def __init__(self, db_path, directories, covers_dir=None, parent=None):
        super().__init__(parent)
        self._db_path = str(db_path)
        self._directories = [str(d) for d in directories]
        self._covers_dir = covers_dir

    def run(self) -> None:
        conn = None
        try:
            # 不调用 db.connect：它会清理 -wal/-shm，主线程连接还开着时不能这么做。
            conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            repository = Repository(conn)
            library = LibraryService(repository, covers_dir=self._covers_dir)
            total = {"added": 0, "skipped": 0, "failed": 0, "total": 0}
            for directory in self._directories:
                last_emit = 0.0

                def on_progress(index: int, count: int, name: str) -> None:
                    nonlocal last_emit
                    now = time.monotonic()
                    if now - last_emit >= 0.1 or index == count:
                        last_emit = now
                        self.progress.emit(index, count, name)

                stats = library.scan(directory, on_progress=on_progress)
                for key in total:
                    total[key] += int(stats.get(key, 0))
            self.finishedScan.emit(total)
        except Exception as err:
            self.finishedScan.emit({"added": 0, "skipped": 0, "failed": 1, "total": 0,
                                    "error": str(err)})
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass


class LibraryPage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._model = TrackTableModel()
        self._scan_worker: ScanWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        self.header = PageHeader("本地库")
        self.header.add_action("播放选中", self.play_selected)
        self.header.add_action("整表入队", self.queue_all)
        self.import_btn = self.header.add_action("导入文件", self.import_files)
        self.scan_btn = self.header.add_action("扫描目录", self.choose_and_scan, primary=True)
        layout.addWidget(self.header)

        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("在本地库中筛选")
        self.filter_input.setClearButtonEnabled(True)
        self.filter_input.textChanged.connect(self.reload)
        filters.addWidget(self.filter_input, 1)
        layout.addLayout(filters)

        self.status = QLabel("")
        self.status.setObjectName("hintLabel")
        self.status.setVisible(False)
        layout.addWidget(self.status)

        self.list = TrackListView()
        self.list.setModel(self._model)
        style_track_list(self.list, "本地库为空\n点右上角「扫描目录」或「导入文件」添加音乐", multi_select=True)
        self.list.doubleClicked.connect(self.play_selected)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        layout.addWidget(self.list, 1)

        self.reload()

    def _set_status(self, text: str) -> None:
        self.status.setText(text)
        self.status.setVisible(bool(text))

    def reload(self) -> None:
        keyword = self.filter_input.text().strip()
        tracks = self.context.repository.list_tracks(keyword=keyword)
        self._model.set_tracks(tracks)
        self.header.set_subtitle(
            f"共 {self.context.repository.count_tracks()} 首 · 当前显示 {len(tracks)} 首")

    def choose_and_scan(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择音乐目录",
                                                     self.context.settings.get("library_dir"))
        if not directory:
            return
        self.start_scan(directory)

    def start_scan(self, directory: str) -> None:
        if self._scan_worker and self._scan_worker.isRunning():
            return
        self.scan_btn.setEnabled(False)
        self._set_status(f"正在扫描 {directory} …")
        self._scan_worker = ScanWorker(self.context.library, directory, self)
        self._scan_worker.finishedScan.connect(self._on_scan_done)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.start()

    def startup_scan(self) -> None:
        """启动后在后台扫描设置里的本地库/下载目录，不阻塞主窗口。"""
        if not bool(self.context.settings.get("startup_scan_enabled", True)):
            return
        if self._scan_worker and self._scan_worker.isRunning():
            return
        directories: list[Path] = []
        for key in ("library_dir", "download_dir"):
            value = str(self.context.settings.get(key) or "").strip()
            if not value:
                continue
            path = Path(value)
            if not path.is_dir():
                continue
            resolved = path.resolve()
            if all(resolved != existing.resolve() for existing in directories):
                directories.append(path)
        if not directories:
            return
        db_path = getattr(self.context, "db_path", None)
        if not db_path:
            return
        db_path = Path(str(db_path))
        if not str(db_path):
            return
        self.scan_btn.setEnabled(False)
        self._set_status("启动扫描：准备中…")
        self._scan_worker = StartupScanWorker(
            db_path, directories, getattr(self.context.library, "covers_dir", None), self)
        self._scan_worker.progress.connect(self._on_startup_progress)
        self._scan_worker.finishedScan.connect(self._on_startup_scan_done)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.start()

    def _on_startup_progress(self, index: int, count: int, name: str) -> None:
        self._set_status(f"启动扫描：{name}（{index}/{count}）")

    def _on_startup_scan_done(self, stats: dict) -> None:
        if stats.get("error"):
            self._set_status(f"启动扫描失败：{stats['error']}")
        else:
            self._set_status(
                f"启动扫描完成：新增 {stats.get('added', 0)}，跳过 {stats.get('skipped', 0)}，"
                f"失败 {stats.get('failed', 0)}，共 {stats.get('total', 0)} 个文件")
        self.reload()

    def _on_scan_done(self, stats: dict) -> None:
        self._set_status(f"扫描完成：新增 {stats.get('added', 0)}，跳过 {stats.get('skipped', 0)}，"
                         f"失败 {stats.get('failed', 0)}，共 {stats.get('total', 0)} 个文件")
        self.reload()

    def _on_scan_finished(self) -> None:
        self.scan_btn.setEnabled(True)

    def import_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音频文件", self.context.settings.get("library_dir"),
            "音频文件 (*.mp3 *.flac *.wav *.m4a *.aac *.ogg *.ape *.wv)",
        )
        if not files:
            return
        added = self.context.library.import_files(files)
        self._set_status(f"已导入 {added} 个文件")
        self.reload()

    def play_selected(self) -> None:
        rows = self.list.selected_rows()
        if not rows:
            return
        tracks = [self._model.track(r) for r in rows]
        tracks = [t for t in tracks if t]
        if tracks:
            self.context.playback.set_queue(tracks, 0)

    def queue_all(self) -> None:
        tracks = [self._model.track(row) for row in range(self._model.rowCount())]
        tracks = [t for t in tracks if t]
        if tracks:
            self.context.playback.set_queue(tracks, 0)

    # ---------------- 右键菜单 ----------------
    def _selected(self):
        rows = self.list.selected_rows()
        if not rows:
            return None
        return self._model.track(rows[0])

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
        menu.addAction("加入歌单…", lambda: self._add_to_playlist(track))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _favorite(self, track) -> None:
        self.context.repository.add_to_playlist("favorites", track)
        self._set_status(f"已收藏：{track.display}")

    def _add_to_playlist(self, track) -> None:
        from shiyin.app.ui.dialogs.playlist_picker import add_track

        message = add_track(self, self.context.repository, track)
        if message:
            self._set_status(message)
