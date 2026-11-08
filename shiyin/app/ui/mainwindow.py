"""主窗口：左侧分组导航 + 顶栏 + 内容区 + 底部播放栏。"""

from __future__ import annotations

from PySide6.QtCore import (QEasingCurve, QEvent, QPropertyAnimation, QRect, QSize, Qt, QTimer)
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                               QMenu, QPushButton, QStackedWidget, QSystemTrayIcon, QToolButton,
                               QVBoxLayout, QWidget)

from shiyin.app.services.session_service import SessionService
from shiyin.app.ui.models.track_model import set_covers_dir
from shiyin.app.ui.pages.downloads_page import DownloadsPage
from shiyin.app.ui.pages.favorites_page import FavoritesPage
from shiyin.app.ui.pages.library_page import LibraryPage
from shiyin.app.ui.pages.playlists_page import PlaylistsPage
from shiyin.app.ui.pages.queue_page import QueuePage
from shiyin.app.ui.pages.recent_page import RecentPage
from shiyin.app.ui.pages.search_page import SearchPage
from shiyin.app.ui.pages.settings_page import SettingsPage
from shiyin.app.ui.theme import stylesheet
from shiyin.app.ui.widgets import icons
from shiyin.app.ui.widgets.lyric_page import LyricPage
from shiyin.app.ui.widgets.player_bar import PlayerBar
from shiyin.app.ui.widgets.track_list import TrackListView, set_dark_mode


def _app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#2ecb71"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 14, 14)
    painter.setPen(QColor("#ffffff"))
    font = painter.font()
    font.setPointSize(30)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "♪")
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    NAV_ITEMS = [("我的收藏", "favorites"), ("最近播放", "recent"), ("播放列表", "queue"), ("本地库", "library"),
                 ("下载", "downloads"), ("歌单", "playlists"), ("设置", "settings")]
    NAV_GROUPS = [("我的音乐", ("favorites", "recent", "queue")),
                  ("资源", ("library", "downloads", "playlists"))]

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("拾音 ShiYin")
        self.setWindowIcon(_app_icon())
        self.resize(1180, 760)
        self.setMinimumSize(960, 640)
        self._theme = str(context.settings.get("theme") or "light").lower()
        self.setStyleSheet(stylesheet(self._theme))
        # 封面目录要在页面构造前注入，delegate 第一次绘制就会用到
        covers_dir = getattr(getattr(context, "library", None), "covers_dir", None)
        if covers_dir:
            set_covers_dir(covers_dir)

        self._labels = {key: label for label, key in self.NAV_ITEMS}
        self._nav_pages = {key: index for index, (_label, key) in enumerate(self.NAV_ITEMS)}
        self._last_keyword = ""

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        body.addWidget(self._build_sidebar())

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        right.addWidget(self._build_topbar())

        self.stack = QStackedWidget()
        self.favorites_page = FavoritesPage(context)
        self.recent_page = RecentPage(context)
        self.queue_page = QueuePage(context)
        self.library_page = LibraryPage(context)
        self.downloads_page = DownloadsPage(context)
        self.playlists_page = PlaylistsPage(context)
        self.settings_page = SettingsPage(context)
        self.search_page = SearchPage(context)  # 搜索页面（不在导航栏中）
        for page in (self.favorites_page, self.recent_page, self.queue_page, self.library_page,
                     self.downloads_page, self.playlists_page, self.settings_page, self.search_page):
            self.stack.addWidget(page)
        # 记录搜索页面的索引
        self._search_page_index = self.stack.count() - 1
        right.addWidget(self.stack, 1)
        body.addLayout(right, 1)
        outer.addLayout(body, 1)

        self.player_bar = PlayerBar(context.playback, getattr(context, "repository", None))
        outer.addWidget(self.player_bar)

        # 队列抽屉（覆盖在内容区右侧，导航页里的播放列表仍然保留）
        self._build_queue_drawer(central)
        central.installEventFilter(self)

        # 歌词页面（覆盖整个中央控件）
        self.lyric_page = LyricPage(context.playback, central)
        self.lyric_page.setGeometry(0, 0, central.width(), central.height())
        self.lyric_page.setVisible(False)
        self.lyric_page.raise_()  # 确保在最上层

        # 添加透明度效果
        self._lyric_opacity_effect = QGraphicsOpacityEffect()
        self._lyric_opacity_effect.setOpacity(1.0)
        self.lyric_page.setGraphicsEffect(self._lyric_opacity_effect)

        # 设置 PlayerBar 的入口回调
        self.player_bar._on_lyric_clicked = self._toggle_lyric_page
        self.player_bar._on_queue_clicked = self._toggle_queue_drawer
        self.settings_page.theme_changed.connect(self._apply_theme)

        # 歌词页面动画
        self._lyric_animation = None

        self.setCentralWidget(central)

        # 导航历史栈
        self._nav_history = []  # 页面索引历史
        self._nav_history_pos = -1  # 当前位置

        self.session = SessionService(context.repository, context.playback, context.settings, self)
        self.session.bind_window(self)

        self._show_page(0, push=True)  # 记录初始页面
        self._setup_tray()
        context.playback.currentChanged.connect(self._on_track_changed)
        self._apply_theme(self._theme)
        self.session.restore()
        # 窗口显示后再后台扫描，避免启动时主线程被文件哈希拖住。
        QTimer.singleShot(0, self.library_page.startup_scan)

    # ---------------- 队列抽屉（P3-1） ----------------
    def _build_queue_drawer(self, parent: QWidget) -> None:
        self.queue_drawer = QFrame(parent)
        self.queue_drawer.setObjectName("queueDrawer")
        self.queue_drawer.setFixedWidth(380)
        self.queue_drawer.hide()

        shadow = QGraphicsDropShadowEffect(self.queue_drawer)
        shadow.setBlurRadius(24)
        shadow.setOffset(-6, 0)
        shadow.setColor(QColor(0, 0, 0, 55))
        self.queue_drawer.setGraphicsEffect(shadow)

        drawer_layout = QVBoxLayout(self.queue_drawer)
        drawer_layout.setContentsMargins(0, 0, 0, 0)
        drawer_layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("drawerHeader")
        header_box = QHBoxLayout(header)
        header_box.setContentsMargins(16, 10, 10, 8)
        header_box.setSpacing(8)
        title = QLabel("播放队列")
        title.setObjectName("pageTitle")
        header_box.addWidget(title)
        self.drawer_count = QLabel("0 首")
        self.drawer_count.setObjectName("pageSubtitle")
        header_box.addWidget(self.drawer_count)
        header_box.addStretch(1)
        self.drawer_clear_btn = QPushButton("清空")
        self.drawer_clear_btn.setObjectName("ghostButton")
        self.drawer_clear_btn.setFixedHeight(28)
        self.drawer_clear_btn.clicked.connect(lambda: self._clear_drawer_queue())
        header_box.addWidget(self.drawer_clear_btn)
        close_btn = QPushButton("×")
        close_btn.setObjectName("iconButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setToolTip("收起队列")
        close_btn.clicked.connect(lambda: self.hide_queue_drawer(True))
        header_box.addWidget(close_btn)
        drawer_layout.addWidget(header)

        self.drawer_queue_page = QueuePage(self.context)
        self.drawer_queue_page.setObjectName("queueDrawerPage")
        # 抽屉里用自带的紧凑标题行，隐藏页面原有页头（导航页那套仍保留）
        self.drawer_queue_page.header.hide()
        self.drawer_queue_page.layout().setContentsMargins(12, 0, 12, 12)
        drawer_layout.addWidget(self.drawer_queue_page, 1)

        self._drawer_animation = None
        self.context.playback.queueChanged.connect(self._update_drawer_header)
        self.context.playback.currentChanged.connect(self._update_drawer_header)
        self._update_drawer_header()

    def _queue_drawer_rect(self) -> QRect:
        # 用主窗口自身的尺寸而不是 centralWidget()：窗口还没 show 时 central 仍是
        # 640×480 的默认尺寸，会把抽屉定位到内容区左边、高度也被截掉一半。
        height = max(200, self.height() - 64 - 88)
        return QRect(self.width() - self.queue_drawer.width(), 64,
                     self.queue_drawer.width(), height)

    def _update_drawer_header(self, *_args) -> None:
        count = len(self.context.playback.queue)
        index = self.context.playback.index
        if count and 0 <= index < count:
            self.drawer_count.setText(f"{count} 首 · 第 {index + 1} 首")
        else:
            self.drawer_count.setText(f"{count} 首" if count else "空")

    def _clear_drawer_queue(self) -> None:
        self.drawer_queue_page.clear_queue()
        self._update_drawer_header()

    def _toggle_queue_drawer(self) -> None:
        if self.queue_drawer.isVisible():
            self.hide_queue_drawer(True)
        else:
            self.show_queue_drawer(True)

    def show_queue_drawer(self, animated: bool = True) -> None:
        if self.lyric_page.isVisible():
            self._hide_lyric_page()
        self.drawer_queue_page.reload()
        self._update_drawer_header()
        target = self._queue_drawer_rect()
        self.queue_drawer.show()
        self.queue_drawer.raise_()
        if not animated:
            self.queue_drawer.setGeometry(target)
            return
        start = QRect(target.x() + target.width(), target.y(), target.width(), target.height())
        self.queue_drawer.setGeometry(start)
        animation = QPropertyAnimation(self.queue_drawer, b"geometry", self)
        animation.setDuration(180)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.setStartValue(start)
        animation.setEndValue(target)
        self._drawer_animation = animation
        animation.start()

    def hide_queue_drawer(self, animated: bool = True) -> None:
        if not self.queue_drawer.isVisible():
            return
        geometry = self.queue_drawer.geometry()
        if not animated:
            self.queue_drawer.hide()
            return
        target = QRect(self.centralWidget().width(), geometry.y(), geometry.width(), geometry.height())
        animation = QPropertyAnimation(self.queue_drawer, b"geometry", self)
        animation.setDuration(160)
        animation.setEasingCurve(QEasingCurve.InCubic)
        animation.setStartValue(geometry)
        animation.setEndValue(target)
        animation.finished.connect(self.queue_drawer.hide)
        self._drawer_animation = animation
        animation.start()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.centralWidget() and event.type() == QEvent.Resize and self.queue_drawer.isVisible():
            self.queue_drawer.setGeometry(self._queue_drawer_rect())
        return super().eventFilter(watched, event)

    # ---------------- 主题（P3-3） ----------------
    def _apply_theme(self, mode: str) -> None:
        mode = "dark" if str(mode).lower() == "dark" else "light"
        self._theme = mode
        dark = mode == "dark"
        self.setStyleSheet(stylesheet(mode))
        set_dark_mode(dark)
        color = "#b8c0cc" if dark else "#4b5563"
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            key = item.data(Qt.UserRole) if item else None
            if key:
                item.setIcon(icons.nav_icon(key, color))
        for key, button in self._shortcut_buttons.items():
            button.setIcon(icons.nav_icon(key, color))
        self.settings_btn.setIcon(icons.nav_icon("settings", color))
        self.search_action.setIcon(icons.search("#9aa4b2" if dark else "#8a8f99"))
        if hasattr(self, "player_bar"):
            self.player_bar.set_theme(dark)
        for view in self.findChildren(TrackListView):
            view.viewport().update()

    # ---------------- 侧栏 ----------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(232)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 14, 12, 12)
        side.setSpacing(8)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(_app_icon().pixmap(32, 32))
        logo.setFixedSize(32, 32)
        brand.addWidget(logo)
        names = QVBoxLayout()
        names.setSpacing(0)
        name = QLabel("拾音")
        name.setObjectName("brandName")
        sub = QLabel("ShiYin · 本地优先")
        sub.setObjectName("brandSub")
        names.addWidget(name)
        names.addWidget(sub)
        brand.addLayout(names, 1)
        side.addLayout(brand)
        side.addSpacing(4)

        shortcuts = QHBoxLayout()
        shortcuts.setSpacing(8)
        self._shortcut_buttons: dict[str, QToolButton] = {}
        for key, text in (("favorites", "收藏"), ("queue", "队列")):
            button = QToolButton()
            button.setObjectName("shortcutButton")
            button.setFixedSize(100, 54)
            button.setText(text)
            button.setIcon(icons.nav_icon(key))
            button.setIconSize(QSize(22, 22))
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.clicked.connect(lambda _checked=False, k=key: self._show_page(self._nav_pages[k]))
            self._shortcut_buttons[key] = button
            shortcuts.addWidget(button)
        side.addLayout(shortcuts)

        new_btn = QPushButton("＋  新建歌单")
        new_btn.setObjectName("dashedButton")
        new_btn.setFixedHeight(36)
        new_btn.clicked.connect(self._new_playlist)
        side.addWidget(new_btn)

        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setFrameShape(QFrame.NoFrame)
        self.nav.setIconSize(QSize(18, 18))
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for group, keys in self.NAV_GROUPS:
            self._add_nav_group(group)
            for key in keys:
                self._add_nav_item(key)
        self.nav.currentRowChanged.connect(self._on_nav)
        side.addWidget(self.nav, 1)

        self.settings_btn = QPushButton("设置")
        self.settings_btn.setObjectName("navButton")
        self.settings_btn.setCheckable(True)
        self.settings_btn.setFixedHeight(40)
        self.settings_btn.setIcon(icons.nav_icon("settings"))
        self.settings_btn.setIconSize(QSize(18, 18))
        self.settings_btn.clicked.connect(lambda: self._show_page(self._nav_pages["settings"]))
        side.addWidget(self.settings_btn)
        return sidebar

    def _add_nav_group(self, text: str) -> None:
        item = QListWidgetItem(text)
        item.setFlags(Qt.NoItemFlags)
        item.setSizeHint(QSize(0, 30))
        font = item.font()
        font.setPointSize(9)
        font.setBold(True)
        item.setFont(font)
        item.setForeground(QColor("#9aa0a6"))
        self.nav.addItem(item)
        if self.nav.count() == 1:
            return

    def _add_nav_item(self, key: str) -> None:
        item = QListWidgetItem(icons.nav_icon(key), self._labels[key])
        item.setData(Qt.UserRole, key)
        item.setSizeHint(QSize(0, 42))
        self.nav.addItem(item)

    def _row_for_key(self, key: str | None) -> int:
        if not key:
            return -1
        for row in range(self.nav.count()):
            item = self.nav.item(row)
            if item and item.data(Qt.UserRole) == key:
                return row
        return -1

    def _new_playlist(self) -> None:
        self.playlists_page.create_playlist()
        self._show_page(self._nav_pages["playlists"])

    # ---------------- 顶栏 ----------------
    def _build_topbar(self) -> QWidget:
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(64)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(6)

        self.back_btn = QPushButton("‹")
        self.back_btn.setObjectName("navArrowBtn")
        self.back_btn.setFixedSize(32, 32)
        self.back_btn.setToolTip("后退")
        self.back_btn.clicked.connect(self._go_back)
        layout.addWidget(self.back_btn)

        self.forward_btn = QPushButton("›")
        self.forward_btn.setObjectName("navArrowBtn")
        self.forward_btn.setFixedSize(32, 32)
        self.forward_btn.setToolTip("前进")
        self.forward_btn.clicked.connect(self._go_forward)
        layout.addWidget(self.forward_btn)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setObjectName("navArrowBtn")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.setToolTip("刷新当前页面")
        self.refresh_btn.clicked.connect(self._refresh_current)
        layout.addWidget(self.refresh_btn)

        self.global_search = QLineEdit()
        self.global_search.setObjectName("searchInput")
        self.global_search.setPlaceholderText("搜索歌曲、歌手，回车搜索")
        self.global_search.setFixedHeight(36)
        self.global_search.setMaximumWidth(420)
        self.search_action = self.global_search.addAction(icons.search("#8a8f99"),
                                                          QLineEdit.LeadingPosition)
        self.global_search.returnPressed.connect(self._on_global_search)
        layout.addSpacing(8)
        layout.addWidget(self.global_search)
        layout.addStretch(1)
        return topbar

    # ---------------- 导航 ----------------
    def _push_nav_history(self, page_index: int) -> None:
        """记录导航历史"""
        # 如果当前位置不是最后，删除当前位置之后的历史（类似浏览器行为）
        if self._nav_history_pos < len(self._nav_history) - 1:
            self._nav_history = self._nav_history[:self._nav_history_pos + 1]
        # 避免重复记录相同的页面
        if not self._nav_history or self._nav_history[-1] != page_index:
            self._nav_history.append(page_index)
            self._nav_history_pos = len(self._nav_history) - 1
        self._update_nav_buttons()

    def _update_nav_buttons(self) -> None:
        """更新前进后退按钮状态"""
        self.back_btn.setEnabled(self._nav_history_pos > 0)
        self.forward_btn.setEnabled(self._nav_history_pos < len(self._nav_history) - 1)

    def _select_nav(self, page_index: int) -> None:
        """让侧栏高亮跟随当前页面（不改页面索引与行号的关系）。"""
        key = self.NAV_ITEMS[page_index][1] if 0 <= page_index < len(self.NAV_ITEMS) else None
        row = self._row_for_key(key)
        self.nav.blockSignals(True)
        if row >= 0:
            self.nav.setCurrentRow(row)
        else:
            self.nav.setCurrentRow(-1)
            self.nav.clearSelection()
        self.nav.blockSignals(False)
        self.settings_btn.setChecked(key == "settings")

    def _show_page(self, page_index: int, push: bool = True) -> None:
        """切换页面：唯一入口，统一处理 stack、高亮、历史与刷新。"""
        if not (0 <= page_index < self.stack.count()):
            return
        self.stack.setCurrentIndex(page_index)
        self._select_nav(page_index)
        if push:
            self._push_nav_history(page_index)
        else:
            self._update_nav_buttons()
        self._reload_page(page_index)
        if page_index < len(self.NAV_ITEMS):
            self.session.note_page(self.NAV_ITEMS[page_index][1])

    def _go_back(self) -> None:
        """后退到上一个页面"""
        if self._nav_history_pos > 0:
            self._nav_history_pos -= 1
            self._show_page(self._nav_history[self._nav_history_pos], push=False)

    def _go_forward(self) -> None:
        """前进到下一个页面"""
        if self._nav_history_pos < len(self._nav_history) - 1:
            self._nav_history_pos += 1
            self._show_page(self._nav_history[self._nav_history_pos], push=False)

    def _reload_page(self, page_index: int) -> None:
        """重新加载页面数据"""
        if page_index < len(self.NAV_ITEMS):
            key = self.NAV_ITEMS[page_index][1]
            if key == "library":
                self.library_page.reload()
            elif key == "favorites":
                self.favorites_page.reload()
            elif key == "recent":
                self.recent_page.reload()
            elif key == "queue":
                self.queue_page.reload()
            elif key == "playlists":
                self.playlists_page.reload()

    def _on_nav(self, row: int) -> None:
        item = self.nav.item(row)
        key = item.data(Qt.UserRole) if item else None
        if not key:
            return
        page_index = self._nav_pages.get(key)
        if page_index is not None:
            self._show_page(page_index, push=True)

    def _refresh_current(self) -> None:
        index = self.stack.currentIndex()
        if index == self._search_page_index:
            if self._last_keyword:
                self.search_page.search(self._last_keyword)
            return
        self._reload_page(index)

    def _on_global_search(self) -> None:
        keyword = self.global_search.text().strip()
        if not keyword:
            return
        # 切换到搜索页面并自动搜索
        self._last_keyword = keyword
        self.stack.setCurrentIndex(self._search_page_index)
        self._select_nav(self._search_page_index)
        self._push_nav_history(self._search_page_index)
        self.search_page.search(keyword)

    def _on_track_changed(self, track) -> None:
        self.setWindowTitle(f"{track.title} - 拾音 ShiYin")

    def _toggle_lyric_page(self) -> None:
        """切换歌词页面显示/隐藏"""
        if self.lyric_page.isVisible():
            self._hide_lyric_page()
        else:
            self._show_lyric_page()

    def _show_lyric_page(self) -> None:
        """显示歌词页面（直接显示）"""
        # 设置歌词页面覆盖整个中央控件
        central = self.centralWidget()
        if central:
            self.lyric_page.setGeometry(0, 0, central.width(), central.height())

        # 直接显示
        self.lyric_page.show_lyric()
        self.lyric_page.setVisible(True)
        self.lyric_page.raise_()

    def _hide_lyric_page(self) -> None:
        """隐藏歌词页面（直接隐藏）"""
        if not self.lyric_page.isVisible():
            return

        # 直接隐藏
        self.lyric_page.setVisible(False)

    # ---------------- 托盘 ----------------
    def _setup_tray(self) -> None:
        """初始化系统托盘 - 完全按照测试程序的方式"""
        self.tray = QSystemTrayIcon(_app_icon(), self)
        self.tray.setToolTip("拾音 ShiYin")

        # 创建菜单（与测试程序完全一致）
        tray_menu = QMenu()

        show_action = tray_menu.addAction("显示主界面")
        show_action.triggered.connect(lambda: self._restore())

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("退出程序")
        quit_action.triggered.connect(lambda: self._force_quit())

        self.tray.setContextMenu(tray_menu)

        # 连接激活信号
        def on_activate(reason):
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                self._restore()
            elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                self._restore()

        self.tray.activated.connect(on_activate)
        self.tray.show()
        self._tray_visible = True

    def _restore(self) -> None:
        """恢复窗口显示 - 与测试程序一致"""
        self.show()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _force_quit(self) -> None:
        """强制退出程序 - 确保所有线程都停止"""
        import os
        import threading
        import time

        if hasattr(self, "session"):
            try:
                self.session.flush()
            except Exception:
                pass

        # 先隐藏托盘图标
        if hasattr(self, 'tray') and self.tray:
            self.tray.hide()
            self.tray.deleteLater()

        # 停止播放
        if hasattr(self, 'context') and self.context:
            if hasattr(self.context, 'playback'):
                try:
                    self.context.playback.stop()
                except:
                    pass
            # 关闭上下文
            try:
                self.context.close()
            except:
                pass

        # 强制退出应用
        QApplication.quit()

        # 等待非守护线程结束（最多 3 秒）
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            alive = [t for t in threading.enumerate()
                     if t is not threading.main_thread() and t.is_alive() and not t.daemon]
            if not alive:
                break
            time.sleep(0.05)

        # 硬退出进程
        os._exit(0)

    def closeEvent(self, event) -> None:
        """关闭窗口时最小化到托盘"""
        if hasattr(self, "session"):
            try:
                self.session.flush()
            except Exception:
                pass
        minimize_to_tray = self.context.settings.get("minimize_to_tray", True)

        if minimize_to_tray and hasattr(self, '_tray_visible') and self._tray_visible:
            event.ignore()
            self.hide()
            # 显示托盘消息提示
            if not self.context.settings.get("close_to_tray_hint_shown", False):
                self.tray.showMessage(
                    "拾音 ShiYin",
                    "应用已最小化到系统托盘，双击托盘图标可恢复窗口",
                    QSystemTrayIcon.Information,
                    3000
                )
                self.context.settings.set("close_to_tray_hint_shown", True)
            return

        # 真正关闭
        if hasattr(self, 'tray'):
            self.tray.hide()
        self.context.close()
        event.accept()
