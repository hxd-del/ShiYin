"""应用入口：一个进程、一个窗口、一个事件循环。

命令行里的重活（搜索、下载、扫描）都在服务层的后台线程里，主线程只跑 Qt 事件循环。
"""

from __future__ import annotations

import json
import os
import sys

from shiyin import APP_DISPLAY_NAME, APP_NAME, __version__


def _arg(args: list[str], flag: str) -> str | None:
    if flag not in args:
        return None
    index = args.index(flag)
    return args[index + 1] if len(args) > index + 1 else ""


def _search_check(args: list[str], keyword: str) -> int:
    """无界面跑一次搜索，把结果写进日志目录，用于核对打包产物（EXE 没有控制台）。"""
    from shiyin.app import paths
    from shiyin.app.context import build_context

    context = build_context(start_cache=False)
    try:
        sources = context.settings.enabled_sources
        override = _arg(args, "--sources")
        if override:
            sources = [s.strip() for s in override.split(",") if s.strip()]
        result = context.search.search(keyword, sources=sources)
        payload = {
            "keyword": keyword,
            "elapsed_ms": result.elapsed_ms,
            "total": len(result.items),
            "per_source": result.per_source,
            "errors": result.errors,
            "items": [
                {"source": t.source, "title": t.title, "artist": t.artist,
                 "ext": t.ext, "has_url": bool(t.url)}
                for t in result.items[:100]
            ],
        }
        out = _arg(args, "--out")
        target = out or str(paths.logs_dir() / "search-check.json")
        from pathlib import Path

        Path(target).parent.mkdir(parents=True, exist_ok=True)
        Path(target).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"elapsed_ms": result.elapsed_ms, "count": len(result.items),
                          "per_source": result.per_source, "errors": result.errors},
                         ensure_ascii=False))
        return 0
    finally:
        context.close()


def main(argv: list[str] | None = None) -> int:
    from shiyin.app import bootstrap

    args = sys.argv if argv is None else argv

    logger = bootstrap.prepare()
    logger.info("%s %s 启动", APP_NAME, __version__)

    keyword = _arg(args, "--search")
    if keyword is not None:
        code = _search_check(args, keyword)
        # 已超时的音源线程还挂在 socket 上，正常解释器退出会被 atexit join 住，
        # 自检进程必须立即结束，否则命令行永远不返回。
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(code)

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv if argv is None else argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setOrganizationName("ShiYin")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")

    from shiyin.app.context import build_context
    from shiyin.app.core.single_instance import SingleInstance
    from shiyin.app.ui.mainwindow import MainWindow

    instance = SingleInstance()
    if not instance.acquire():
        return 0

    try:
        context = build_context()
    except Exception:
        logger.exception("服务初始化失败")
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.critical(None, "拾音", "初始化失败，详情见日志目录。")
        return 1

    window = MainWindow(context)
    instance.on_activate(window._restore)
    window.show()

    if "--selftest" in args:
        # 打包后自检：窗口起来 1.5 秒后自动退出
        from PySide6.QtCore import QTimer

        QTimer.singleShot(1500, app.quit)

    code = app.exec()
    context.close()
    _ensure_exit(code)
    return code


def _ensure_exit(code: int) -> None:
    """关窗时若还有音源请求线程挂在 socket 上，最多等 3 秒就硬退出，别让进程残留。"""
    import logging
    import threading
    import time

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        alive = [t for t in threading.enumerate()
                 if t is not threading.main_thread() and t.is_alive() and not t.daemon]
        if not alive:
            return
        time.sleep(0.05)
    logging.shutdown()
    os._exit(code)


if __name__ == "__main__":
    raise SystemExit(main())
