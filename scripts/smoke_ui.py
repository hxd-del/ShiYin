"""界面冒烟：离屏创建主窗口，确认所有页面与信号连接没有构造期异常。

运行：.venv\\Scripts\\python.exe scripts\\smoke_ui.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from shiyin.app.context import build_context  # noqa: E402
from shiyin.app.ui.mainwindow import MainWindow  # noqa: E402


def main() -> None:
    app = QApplication(sys.argv)
    work = Path(tempfile.mkdtemp(prefix="shiyin-ui-"))
    context = build_context(data_dir=work, start_cache=True)
    window = MainWindow(context)
    window.show()
    for _ in range(5):
        app.processEvents()

    # 导航行号与页面索引已经解耦，按 key 切页
    pages = [("library", window.library_page), ("downloads", window.downloads_page),
             ("playlists", window.playlists_page), ("settings", window.settings_page)]
    for key, page in pages:
        window._show_page(window._nav_pages[key])
        app.processEvents()
        print("page ok:", type(page).__name__)

    # 播放栏信号连通性：手动切换状态不触发真实播放
    bar = window.player_bar
    bar._on_state("playing")
    assert bar.play_btn.toolTip() == "暂停"
    bar._on_duration(180000)
    assert bar.dur_label.text() == "03:00"
    print("player bar ok")

    window.tray.hide()
    context.close()
    print("界面冒烟通过")


if __name__ == "__main__":
    main()
