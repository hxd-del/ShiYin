"""下载页：任务列表、进度、暂停/继续/取消/重试。"""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from shiyin.app.adapters.source_catalog import source_label
from shiyin.app.adapters.progress_bridge import ProgressBridge
from shiyin.app.core.models import DownloadStatus, DownloadTask

HEADERS = ["曲目", "来源", "状态", "进度", "速度", "大小"]


class DownloadsPage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._ids: list[str] = []
        self._tasks: dict[str, DownloadTask] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 12)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.summary = QLabel("暂无下载任务")
        self.summary.setObjectName("hintLabel")
        top.addWidget(self.summary, 1)
        for text, handler in [("暂停", self.pause_current), ("继续", self.resume_current),
                              ("取消", self.cancel_current), ("重试", self.retry_current),
                              ("打开目录", self.open_dir)]:
            btn = QPushButton(text)
            btn.setObjectName("ghostButton")
            btn.clicked.connect(handler)
            top.addWidget(btn)
        layout.addLayout(top)

        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 320)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 110)
        self.table.setColumnWidth(4, 110)
        layout.addWidget(self.table, 1)

        self.bridge = ProgressBridge(self.context.downloads.snapshot, parent=self)
        self.bridge.updated.connect(self._on_update)
        self.bridge.start()

    # ---------------- 刷新 ----------------
    def _on_update(self, tasks: list[DownloadTask]) -> None:
        ids = [t.task_id for t in tasks]
        self._tasks = {t.task_id: t for t in tasks}
        if ids != self._ids:
            self._ids = ids
            self.table.setRowCount(len(tasks))
            for row, task in enumerate(tasks):
                for col in range(len(HEADERS)):
                    item = QTableWidgetItem("")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(row, col, item)
        for row, task in enumerate(tasks):
            # 状态列：显示完整错误信息
            status_text = task.status_text
            if task.error and task.status == DownloadStatus.FAILED:
                status_text = f"失败: {task.error}"
            
            values = [
                task.track.display,
                source_label(task.track.source),
                status_text,
                f"{task.percent}%",
                task.speed_text,
                task.track.size_text,
            ]
            for col, value in enumerate(values):
                item = self.table.item(row, col)
                if item and item.text() != value:
                    item.setText(value)
                    # 为状态列添加工具提示，显示完整错误
                    if col == 2 and task.error:
                        item.setToolTip(task.error)
        active = self.context.downloads.active_count()
        done = sum(1 for t in tasks if t.status == DownloadStatus.DONE)
        failed = sum(1 for t in tasks if t.status == DownloadStatus.FAILED)
        self.summary.setText(f"共 {len(tasks)} 个任务，进行中 {active}，完成 {done}，失败 {failed}")

    # ---------------- 操作 ----------------
    def _current_id(self) -> str | None:
        row = self.table.currentRow()
        if 0 <= row < len(self._ids):
            return self._ids[row]
        return None

    def _on(self, action, label: str) -> None:
        task_id = self._current_id()
        if not task_id:
            self.summary.setText("先选中一个任务")
            return
        action(task_id)
        self.summary.setText(f"{label}：{self._tasks[task_id].track.display}")

    def pause_current(self) -> None:
        self._on(self.context.downloads.pause, "已暂停")

    def resume_current(self) -> None:
        self._on(self.context.downloads.resume, "已继续")

    def cancel_current(self) -> None:
        self._on(self.context.downloads.cancel, "已取消")

    def retry_current(self) -> None:
        self._on(self.context.downloads.retry, "已重试")

    def open_dir(self) -> None:
        path = self.context.settings.get("download_dir")
        if not path or not os.path.isdir(path):
            return
        if sys.platform == "win32":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
