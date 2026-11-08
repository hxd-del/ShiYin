"""主题：浅色 / 深色两套 QSS，不引入第三方样式库。

配色参照 QQ 音乐桌面端：白底卡片 + 浅灰侧栏 + #2ecb71 主色。
深色模式沿用同一套结构，只替换背景、文字与分割线。
"""

from __future__ import annotations

LIGHT = """
* { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; font-size: 13px; }
QWidget { background: #f7f8fa; color: #1f2937; }
QLabel { background: transparent; }

/* ---------- 侧栏 ---------- */
QWidget#sidebar { background: #f7f7f7; border-right: 1px solid #ececec; }
QLabel#brandName { font-size: 14px; font-weight: 600; color: #111827; }
QLabel#brandSub { font-size: 10px; color: #9aa0a6; }
QListWidget#nav {
    background: transparent; border: none; border-radius: 0; padding: 0 2px; outline: 0;
}
QListWidget#nav::item {
    padding: 0 10px; border-radius: 8px; color: #4b5563;
    border-left: 3px solid transparent;
}
QListWidget#nav::item:hover { background: #eef0f2; }
QListWidget#nav::item:selected {
    background: #eef0f2; color: #111827; border-left: 3px solid #2ecb71;
}
QPushButton#navButton {
    background: transparent; border: none; text-align: left;
    padding: 0 12px; color: #4b5563; border-radius: 8px;
}
QPushButton#navButton:hover { background: #eef0f2; }
QPushButton#navButton:checked { background: #eef0f2; color: #111827; }
QToolButton#shortcutButton {
    background: #f1f2f4; border: none; border-radius: 10px;
    color: #374151; font-size: 12px; padding-top: 8px;
}
QToolButton#shortcutButton:hover { background: #e9ebee; }
QPushButton#dashedButton {
    background: transparent; border: 1px dashed #cfd4da; border-radius: 8px;
    color: #6b7280; padding: 6px 10px; text-align: left;
}
QPushButton#dashedButton:hover { border-color: #2ecb71; color: #2ecb71; }

/* ---------- 顶栏 ---------- */
QLineEdit#searchInput {
    background: #f2f3f5; border: none; border-radius: 18px;
    padding: 0 14px; min-height: 36px; color: #1f2937;
}
QLineEdit#searchInput:focus { background: #eceef1; }
QPushButton#navArrowBtn {
    background: transparent; border: none; font-size: 20px; color: #4b5563; padding: 0;
}
QPushButton#navArrowBtn:hover { color: #2ecb71; }
QPushButton#navArrowBtn:disabled { color: #cbd5e1; }

/* ---------- 播放条 ---------- */
QFrame#playerBar { background: #ffffff; border-top: 1px solid #eceff3; }
QFrame#playerBar QLabel { background: transparent; }
QWidget#barInfo, QWidget#barCenter, QWidget#barRight { background: transparent; }
QLabel#trackTitle { font-size: 15px; font-weight: 600; color: #111827; }
QLabel#trackArtist { color: #8a8f99; font-size: 12px; }
QLabel#timeLabel { color: #8a8f99; font-size: 12px; }
QLabel#hintLabel { color: #8a8f99; }
QLabel#sectionTitle { font-size: 20px; font-weight: 600; color: #111827; }
QLabel#pageTitle { font-size: 20px; font-weight: 600; color: #111827; }
QLabel#pageSubtitle { font-size: 12px; color: #8a8f99; }
QLabel#cardTitle { font-size: 15px; font-weight: 600; color: #111827; }
QLabel#cardHint { font-size: 12px; color: #8a8f99; }
QPushButton#linkButton {
    background: transparent; border: none; color: #8a8f99;
    padding: 2px 8px; font-size: 12px;
}
QPushButton#linkButton:hover { color: #2ecb71; }
QLabel#cover {
    background: #eafaf0; border-radius: 10px; color: #2ecb71;
    font-size: 22px; font-weight: 600;
}
QPushButton#iconButton {
    background: transparent; border: none; border-radius: 8px; padding: 0;
}
QPushButton#iconButton:hover { background: #f2f3f5; }
QPushButton#playButton {
    background: #2ecb71; border: none; border-radius: 22px; padding: 0;
}
QPushButton#playButton:hover { background: #28b565; }
QPushButton#playButton:pressed { background: #23a55a; }
QPushButton#lyricButton {
    background: transparent; border: none; color: #4b5563;
    font-size: 15px; border-radius: 6px; padding: 0;
}
QPushButton#lyricButton:hover { background: #f2f3f5; color: #2ecb71; }

/* ---------- 通用控件 ---------- */
QLineEdit, QSpinBox, QComboBox {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 6px 10px;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #2ecb71; }
QPushButton {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 6px 14px; color: #1f2937;
}
QPushButton:hover { background: #f7f8fa; }
QPushButton:pressed { background: #eef0f2; }
QPushButton:disabled { color: #b0b5bd; }
QPushButton#primaryButton {
    background: #2ecb71; border: none; color: #ffffff; font-weight: 600;
}
QPushButton#primaryButton:hover { background: #28b565; }
QPushButton#primaryButton:pressed { background: #23a55a; }
QPushButton#ghostButton {
    background: transparent; border: none; color: #4b5563; padding: 6px 10px;
}
QPushButton#ghostButton:hover { background: #f2f3f5; }
QPushButton#panelButton {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px;
    padding: 4px 6px; font-size: 12px; color: #4b5563;
}
QPushButton#panelButton:hover { border-color: #2ecb71; color: #2ecb71; }
QPushButton#panelButton:disabled { color: #b0b5bd; border-color: #eceff3; }

/* ---------- 列表 ---------- */
QListView {
    background: #ffffff; border: none; border-radius: 12px;
    outline: 0; selection-background-color: transparent;
}
QListView#playlistList { background: transparent; border-radius: 0; }
QListWidget#playlistList { background: transparent; border-radius: 0; padding: 0; }
QListWidget#playlistList::item {
    height: 36px; padding: 0 10px; border-radius: 8px; color: #4b5563;
}
QListWidget#playlistList::item:hover { background: #f2f3f5; }
QListWidget#playlistList::item:selected { background: #eafaf0; color: #111827; }
QFrame#settingsCard, QFrame#sidePanel {
    background: #ffffff; border: none; border-radius: 12px;
}
QFrame#queueDrawer {
    background: #ffffff; border: none; border-left: 1px solid #eceff3;
}
QWidget#drawerHeader { background: transparent; }
QWidget#queueDrawerPage { background: transparent; }
QScrollArea#settingsScroll { background: transparent; border: none; }
QWidget#settingsBody { background: transparent; }
QTableView, QTreeWidget, QListWidget {
    background: #ffffff; alternate-background-color: #ffffff;
    border: none; border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: #eafaf0; selection-color: #111827;
    outline: 0;
}
QTableView::item { padding: 0 10px; border: none; }
QHeaderView::section {
    background: #ffffff; color: #8a8f99; border: none;
    border-bottom: 1px solid #f0f2f5; padding: 10px; font-size: 12px;
}
QMenu { background: #ffffff; border: 1px solid #e9ecf1; border-radius: 8px; padding: 4px; }
QMenu::item { padding: 6px 18px; border-radius: 6px; }
QMenu::item:selected { background: #eafaf0; color: #111827; }

/* ---------- 滑块 / 滚动条 ---------- */
QSlider { background: transparent; }
QSlider::groove:horizontal { height: 4px; background: transparent; border-radius: 2px; }
QSlider::add-page:horizontal { background: transparent; }
QSlider::handle:horizontal {
    width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; background: #2ecb71;
}
QSlider::handle:horizontal:hover { background: #28b565; }
QSlider::sub-page:horizontal { background: #2ecb71; border-radius: 2px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #d7dbe1; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #c3c9d1; }
QScrollBar:horizontal { background: transparent; height: 8px; }
QScrollBar::handle:horizontal { background: #d7dbe1; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QCheckBox { spacing: 6px; }
"""

DARK = """
* { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; font-size: 13px; }
QWidget { background: #14161a; color: #e6e8eb; }
QLabel { background: transparent; }

/* ---------- 侧栏 ---------- */
QWidget#sidebar { background: #101216; border-right: 1px solid #262a32; }
QLabel#brandName { font-size: 14px; font-weight: 600; color: #f1f3f5; }
QLabel#brandSub { font-size: 10px; color: #8b96a5; }
QListWidget#nav {
    background: transparent; border: none; border-radius: 0; padding: 0 2px; outline: 0;
}
QListWidget#nav::item {
    padding: 0 10px; border-radius: 8px; color: #b8c0cc;
    border-left: 3px solid transparent;
}
QListWidget#nav::item:hover { background: #1c2027; }
QListWidget#nav::item:selected {
    background: #1c2a2e; color: #f1f3f5; border-left: 3px solid #2ecb71;
}
QPushButton#navButton {
    background: transparent; border: none; text-align: left;
    padding: 0 12px; color: #b8c0cc; border-radius: 8px;
}
QPushButton#navButton:hover { background: #1c2027; }
QPushButton#navButton:checked { background: #1c2027; color: #f1f3f5; }
QToolButton#shortcutButton {
    background: #1c2027; border: none; border-radius: 10px;
    color: #d5dae2; font-size: 12px; padding-top: 8px;
}
QToolButton#shortcutButton:hover { background: #23272f; }
QPushButton#dashedButton {
    background: transparent; border: 1px dashed #3a414d; border-radius: 8px;
    color: #8b96a5; padding: 6px 10px; text-align: left;
}
QPushButton#dashedButton:hover { border-color: #2ecb71; color: #2ecb71; }

/* ---------- 顶栏 ---------- */
QLineEdit#searchInput {
    background: #1f232a; border: none; border-radius: 18px;
    padding: 0 14px; min-height: 36px; color: #e6e8eb;
}
QLineEdit#searchInput:focus { background: #23272f; }
QPushButton#navArrowBtn {
    background: transparent; border: none; font-size: 20px; color: #b8c0cc; padding: 0;
}
QPushButton#navArrowBtn:hover { color: #2ecb71; }
QPushButton#navArrowBtn:disabled { color: #4b5563; }

/* ---------- 播放条 ---------- */
QFrame#playerBar { background: #1b1e24; border-top: 1px solid #262a32; }
QFrame#playerBar QLabel { background: transparent; }
QWidget#barInfo, QWidget#barCenter, QWidget#barRight { background: transparent; }
QLabel#trackTitle { font-size: 15px; font-weight: 600; color: #f1f3f5; }
QLabel#trackArtist { color: #9aa4b2; font-size: 12px; }
QLabel#timeLabel { color: #9aa4b2; font-size: 12px; }
QLabel#hintLabel { color: #9aa4b2; }
QLabel#sectionTitle { font-size: 20px; font-weight: 600; color: #f1f3f5; }
QLabel#pageTitle { font-size: 20px; font-weight: 600; color: #f1f3f5; }
QLabel#pageSubtitle { font-size: 12px; color: #9aa4b2; }
QLabel#cardTitle { font-size: 15px; font-weight: 600; color: #f1f3f5; }
QLabel#cardHint { font-size: 12px; color: #9aa4b2; }
QPushButton#linkButton {
    background: transparent; border: none; color: #9aa4b2;
    padding: 2px 8px; font-size: 12px;
}
QPushButton#linkButton:hover { color: #2ecb71; }
QLabel#cover {
    background: #23272f; border-radius: 10px; color: #6ee7b7;
    font-size: 22px; font-weight: 600;
}
QPushButton#iconButton {
    background: transparent; border: none; border-radius: 8px; padding: 0;
}
QPushButton#iconButton:hover { background: #23272f; }
QPushButton#playButton {
    background: #2ecb71; border: none; border-radius: 22px; padding: 0;
}
QPushButton#playButton:hover { background: #28b565; }
QPushButton#playButton:pressed { background: #23a55a; }
QPushButton#lyricButton {
    background: transparent; border: none; color: #b8c0cc;
    font-size: 15px; border-radius: 6px; padding: 0;
}
QPushButton#lyricButton:hover { background: #23272f; color: #2ecb71; }

/* ---------- 通用控件 ---------- */
QLineEdit, QSpinBox, QComboBox {
    background: #1f232a; border: 1px solid #2c313a; border-radius: 8px; padding: 6px 10px;
    color: #e6e8eb;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #2ecb71; }
QPushButton {
    background: #23272f; border: 1px solid #323844; border-radius: 8px;
    padding: 6px 14px; color: #e6e8eb;
}
QPushButton:hover { background: #2a2f39; }
QPushButton:pressed { background: #1d2128; }
QPushButton:disabled { color: #6b7280; }
QPushButton#primaryButton {
    background: #2ecb71; border: none; color: #ffffff; font-weight: 600;
}
QPushButton#primaryButton:hover { background: #28b565; }
QPushButton#primaryButton:pressed { background: #23a55a; }
QPushButton#ghostButton {
    background: transparent; border: none; color: #b8c0cc; padding: 6px 10px;
}
QPushButton#ghostButton:hover { background: #23272f; }
QPushButton#panelButton {
    background: #20242b; border: 1px solid #323844; border-radius: 8px;
    padding: 4px 6px; font-size: 12px; color: #b8c0cc;
}
QPushButton#panelButton:hover { border-color: #2ecb71; color: #2ecb71; }
QPushButton#panelButton:disabled { color: #6b7280; border-color: #2c313a; }

/* ---------- 列表 ---------- */
QListView {
    background: #1a1d23; border: none; border-radius: 12px;
    outline: 0; selection-background-color: transparent;
}
QListView#playlistList { background: transparent; border-radius: 0; }
QListWidget#playlistList { background: transparent; border-radius: 0; padding: 0; }
QListWidget#playlistList::item {
    height: 36px; padding: 0 10px; border-radius: 8px; color: #b8c0cc;
}
QListWidget#playlistList::item:hover { background: #23272f; }
QListWidget#playlistList::item:selected { background: #1c2a2e; color: #f1f3f5; }
QFrame#settingsCard, QFrame#sidePanel {
    background: #1a1d23; border: none; border-radius: 12px;
}
QFrame#queueDrawer {
    background: #1b1e24; border: none; border-left: 1px solid #262a32;
}
QWidget#drawerHeader { background: transparent; }
QWidget#queueDrawerPage { background: transparent; }
QScrollArea#settingsScroll { background: transparent; border: none; }
QWidget#settingsBody { background: transparent; }
QTableView, QTreeWidget, QListWidget {
    background: #1a1d23; alternate-background-color: #1a1d23;
    border: none; border-radius: 12px;
    gridline-color: transparent;
    selection-background-color: #1c2a2e; selection-color: #f1f3f5;
    outline: 0;
}
QTableView::item { padding: 0 10px; border: none; }
QHeaderView::section {
    background: #20242b; color: #9aa4b2; border: none;
    border-bottom: 1px solid #262a32; padding: 10px; font-size: 12px;
}
QMenu { background: #1f232a; border: 1px solid #2c313a; border-radius: 8px; padding: 4px; }
QMenu::item { padding: 6px 18px; border-radius: 6px; }
QMenu::item:selected { background: #1c2a2e; color: #f1f3f5; }

/* ---------- 滑块 / 滚动条 ---------- */
QSlider { background: transparent; }
QSlider::groove:horizontal { height: 4px; background: transparent; border-radius: 2px; }
QSlider::add-page:horizontal { background: transparent; }
QSlider::handle:horizontal {
    width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; background: #2ecb71;
}
QSlider::handle:horizontal:hover { background: #28b565; }
QSlider::sub-page:horizontal { background: #2ecb71; border-radius: 2px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #333a45; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3f4753; }
QScrollBar:horizontal { background: transparent; height: 8px; }
QScrollBar::handle:horizontal { background: #333a45; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QCheckBox { spacing: 6px; }
"""


def stylesheet(theme: str = "light") -> str:
    return DARK if str(theme).lower() == "dark" else LIGHT
