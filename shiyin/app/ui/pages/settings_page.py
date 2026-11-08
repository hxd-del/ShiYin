"""设置页：目录、下载、搜索、缓存、音源开关（第二批改为分区卡片）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QScrollArea, QSpinBox, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from shiyin.app import paths
from shiyin.app.adapters import source_catalog
from shiyin.app.ui.widgets.page_header import PageHeader


class SourceProbe(QThread):
    """并发试搜一遍，把每个源能不能出结果、要多久报给界面。"""

    partialReady = Signal(str, int, str)  # source, 条数, 错误
    finishedAll = Signal(int, int)

    def __init__(self, adapter, keyword: str, sources: list[str], parent=None):
        super().__init__(parent)
        self._adapter = adapter
        self._keyword = keyword
        self._sources = sources

    def run(self) -> None:
        ok = 0

        def on_source(source: str, tracks, error) -> None:
            nonlocal ok
            count = len(tracks or [])
            if count:
                ok += 1
            self.partialReady.emit(source, count, error or "")

        try:
            self._adapter.search(self._keyword, self._sources, timeout=10.0, on_source=on_source)
        finally:
            self.finishedAll.emit(ok, len(self._sources))


class SettingsPage(QWidget):
    theme_changed = Signal(str)

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        settings = context.settings

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(10)

        self.header = PageHeader("设置")
        self.header.set_subtitle("目录、搜索、缓存与音源")
        self.header.add_action("保存设置", self.save, primary=True)
        layout.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("settingsScroll")
        body = QWidget()
        body.setObjectName("settingsBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 8, 0)
        body_layout.setSpacing(12)

        # ---------- 卡片 1：目录与下载 ----------
        card, card_layout = self._card("目录与下载", "音乐存到哪里、同时下载几首")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(8)
        self.download_dir = QLineEdit(settings.get("download_dir"))
        form.addRow("下载目录", self._path_row(self.download_dir))
        self.library_dir = QLineEdit(settings.get("library_dir"))
        form.addRow("本地库目录", self._path_row(self.library_dir))
        self.concurrency = QSpinBox()
        self.concurrency.setRange(1, 10)
        self.concurrency.setValue(int(settings.get("concurrency") or 6))
        form.addRow("同时下载数", self.concurrency)
        card_layout.addLayout(form)
        body_layout.addWidget(card)

        # ---------- 卡片 2：启动与记忆 ----------
        card, card_layout = self._card("启动与记忆", "记住上次的队列、曲目与页面；启动扫描不阻塞窗口")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(8)
        self.startup_restore = QCheckBox("启动时恢复上次播放")
        self.startup_restore.setChecked(bool(settings.get("startup_restore_enabled", True)))
        self.startup_restore.setToolTip("恢复队列、当前曲目、播放位置和上次页面；默认停在上次位置，不自动出声")
        form.addRow("恢复会话", self.startup_restore)
        self.resume_autoplay = QCheckBox("恢复后自动续播")
        self.resume_autoplay.setChecked(bool(settings.get("resume_autoplay", False)))
        self.resume_autoplay.setToolTip("默认关闭；打开后启动会直接出声，可能吓一跳")
        form.addRow("自动续播", self.resume_autoplay)
        self.startup_scan = QCheckBox("启动时扫描本地库")
        self.startup_scan.setChecked(bool(settings.get("startup_scan_enabled", True)))
        self.startup_scan.setToolTip("扫描本地库目录与下载目录，仅新增/补歌词，不影响现有曲目")
        form.addRow("启动扫描", self.startup_scan)

        data_dir = paths.data_dir()
        db_path = Path(str(context.db_path)) if getattr(context, "db_path", None) else data_dir / "library.db"
        for label, value in (
            ("数据目录", str(data_dir)),
            ("数据库", str(db_path)),
            ("本地库目录", str(settings.get("library_dir") or "")),
        ):
            form.addRow(label, self._readonly_path_row(value))
        card_layout.addLayout(form)
        body_layout.addWidget(card)

        # ---------- 卡片 3：搜索与缓存 ----------
        card, card_layout = self._card("搜索与缓存", "结果条数、等待时间与试听缓存占用")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(8)
        self.search_size = QSpinBox()
        self.search_size.setRange(1, 30)
        self.search_size.setToolTip("每个音源最多取几条；设得越大单源耗时越长，能赶在超时前完成的源反而更少")
        self.search_size.setValue(int(settings.get("search_size_per_source") or 5))
        form.addRow("每源结果数", self.search_size)
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 120)
        self.timeout.setToolTip("单次搜索总等待时间；界面边搜边出结果，设长一些能等到更多慢源")
        self.timeout.setValue(int(settings.get("search_timeout_seconds") or 20))
        form.addRow("搜索超时（秒）", self.timeout)
        self.cache_limit = QSpinBox()
        self.cache_limit.setRange(100, 20000)
        self.cache_limit.setSingleStep(100)
        self.cache_limit.setValue(int(settings.get("cache_limit_mb") or 2048))
        form.addRow("试听缓存上限（MB）", self.cache_limit)
        card_layout.addLayout(form)
        body_layout.addWidget(card)

        # ---------- 卡片 3：外观 ----------
        card, card_layout = self._card("外观", "切换后立即生效，并记住选择")
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setSpacing(8)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("浅色", "light")
        self.theme_combo.addItem("深色", "dark")
        current_theme = str(settings.get("theme") or "light").lower()
        self.theme_combo.setCurrentIndex(1 if current_theme == "dark" else 0)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        form.addRow("主题", self.theme_combo)
        card_layout.addLayout(form)
        body_layout.addWidget(card)

        # ---------- 卡片 4：音源 ----------
        card, card_layout = self._card("音源", "勾选后参与搜索；建议先检测，只留可用的")
        self.sources = QTreeWidget()
        self.sources.setHeaderLabels(["音源", "标识", "检测"])
        self.sources.setRootIsDecorated(False)
        self.sources.setColumnWidth(0, 160)
        self.sources.setMinimumHeight(320)
        enabled = set(settings.enabled_sources)
        for _group, names in source_catalog.groups().items():
            for name in names:
                item = QTreeWidgetItem([f"{source_catalog.source_label(name)}", name, ""])
                item.setCheckState(0, Qt.Checked if name in enabled else Qt.Unchecked)
                item.setData(0, Qt.UserRole, name)
                self.sources.addTopLevelItem(item)
        card_layout.addWidget(self.sources)

        actions = QHBoxLayout()
        self.status = QLabel("")
        self.status.setObjectName("hintLabel")
        self.status.setWordWrap(True)
        actions.addWidget(self.status, 1)
        self.detect_btn = QPushButton("检测音源")
        self.detect_btn.setObjectName("ghostButton")
        self.detect_btn.clicked.connect(self.detect_sources)
        actions.addWidget(self.detect_btn)
        reset_btn = QPushButton("恢复默认音源")
        reset_btn.setObjectName("ghostButton")
        reset_btn.clicked.connect(self.reset_sources)
        actions.addWidget(reset_btn)
        card_layout.addLayout(actions)
        body_layout.addWidget(card)
        body_layout.addStretch(1)

        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        self._probe: SourceProbe | None = None
        self._items: dict[str, QTreeWidgetItem] = {}
        for index in range(self.sources.topLevelItemCount()):
            item = self.sources.topLevelItem(index)
            self._items[item.data(0, Qt.UserRole)] = item

    def _card(self, title: str, hint: str = ""):
        card = QFrame()
        card.setObjectName("settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        card_layout.addWidget(title_label)
        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("cardHint")
            hint_label.setWordWrap(True)
            card_layout.addWidget(hint_label)
        return card, card_layout

    # ---------------- 音源检测 ----------------
    def detect_sources(self) -> None:
        if self._probe and self._probe.isRunning():
            return
        checked = self.selected_sources()
        targets = checked or [item.data(0, Qt.UserRole) for item in self._items.values()]
        self.detect_btn.setEnabled(False)
        self.status.setText(f"正在检测 {len(targets)} 个音源（每个最多 10 秒），可继续使用界面…")
        for item in self._items.values():
            item.setText(2, "…")
        self._probe = SourceProbe(self.context.search.adapter, "晴天", targets, self)
        self._probe.partialReady.connect(self._on_probe_source)
        self._probe.finishedAll.connect(self._on_probe_done)
        self._probe.start()

    def _on_probe_source(self, source: str, count: int, error: str) -> None:
        item = self._items.get(source)
        if item is None:
            return
        item.setText(2, f"{count} 条" if count else ("超时" if not error else "无结果"))

    def _on_probe_done(self, ok: int, total: int) -> None:
        self.detect_btn.setEnabled(True)
        self.status.setText(f"检测完成：{total} 个源里 {ok} 个有结果，其余可取消勾选后搜索更快")

    def _path_row(self, edit: QLineEdit) -> QWidget:
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(edit, 1)
        btn = QPushButton("选择")
        btn.setObjectName("ghostButton")
        btn.clicked.connect(lambda: self._pick_dir(edit))
        box.addWidget(btn)
        return row

    def _readonly_path_row(self, value: str) -> QWidget:
        row = QWidget()
        box = QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        label = QLabel(value)
        label.setObjectName("cardHint")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        box.addWidget(label, 1)
        btn = QPushButton("打开")
        btn.setObjectName("ghostButton")
        btn.clicked.connect(lambda _checked=False, v=value: self._open_path(v))
        box.addWidget(btn)
        return row

    def _open_path(self, value: str) -> None:
        if not value:
            return
        target = Path(value)
        if target.is_file():
            target = target.parent
        if not target.exists():
            self.status.setText(f"目录不存在：{target}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    def _pick_dir(self, edit: QLineEdit) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择目录", edit.text())
        if directory:
            edit.setText(directory)

    # ---------------- 主题 ----------------
    def _on_theme_changed(self, _index: int) -> None:
        mode = self.theme_combo.currentData() or "light"
        self.context.settings.set("theme", mode)
        self.theme_changed.emit(mode)
        self.status.setText("主题已切换：深色模式立即生效" if mode == "dark" else "主题已切换：浅色模式立即生效")

    # ---------------- 保存 ----------------
    def selected_sources(self) -> list[str]:
        result = []
        for index in range(self.sources.topLevelItemCount()):
            item = self.sources.topLevelItem(index)
            if item.checkState(0) == Qt.Checked:
                result.append(item.data(0, Qt.UserRole))
        return result

    def reset_sources(self) -> None:
        enabled = set(source_catalog.default_enabled_sources())
        for index in range(self.sources.topLevelItemCount()):
            item = self.sources.topLevelItem(index)
            item.setCheckState(0, Qt.Checked if item.data(0, Qt.UserRole) in enabled else Qt.Unchecked)
        self.status.setText("已恢复默认音源，记得保存")

    def save(self) -> None:
        sources = self.selected_sources()
        if not sources:
            self.status.setText("至少要保留一个音源")
            return
        self.context.settings.update({
            "download_dir": self.download_dir.text().strip(),
            "library_dir": self.library_dir.text().strip(),
            "concurrency": self.concurrency.value(),
            "search_size_per_source": self.search_size.value(),
            "cache_limit_mb": self.cache_limit.value(),
            "search_timeout_seconds": self.timeout.value(),
            "enabled_sources": sources,
            "theme": self.theme_combo.currentData() or "light",
            "startup_restore_enabled": self.startup_restore.isChecked(),
            "resume_autoplay": self.resume_autoplay.isChecked(),
            "startup_scan_enabled": self.startup_scan.isChecked(),
        })
        self.status.setText(f"已保存（{len(sources)} 个音源），部分设置重启后生效")
