"""启动引导：目录、日志、控制台守卫、崩溃转储。

在无控制台的 EXE 里 sys.stdout 可能是 None，而上游 rich 进度条会直接写 stdout，
所以启动第一步就是把标准输出重定向到日志文件。
"""

from __future__ import annotations

import datetime
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from shiyin.app import paths

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def guard_streams() -> None:
    """把 stdout/stderr 落到文件，避免 --noconsole 下写入 None 触发异常。"""
    needs_guard = getattr(sys, "stdout", None) is None or getattr(sys, "stderr", None) is None
    if not needs_guard and not paths.is_frozen():
        return
    log_path = paths.logs_dir() / "console.log"
    stream = open(log_path, "a", encoding="utf-8", buffering=1)
    if getattr(sys, "stdout", None) is None:
        sys.stdout = stream
    if getattr(sys, "stderr", None) is None:
        sys.stderr = stream


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("shiyin")
    if logger.handlers:
        return logger
    logger.setLevel(level)
    handler = RotatingFileHandler(paths.logs_dir() / "shiyin.log", maxBytes=5 * 1024 * 1024,
                                  backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)
    if getattr(sys, "stdout", None) is not None and not paths.is_frozen():
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(logging.Formatter(_LOG_FORMAT))
        console.setLevel(logging.WARNING)
        logger.addHandler(console)
    logger.propagate = False
    return logger


def install_excepthook(logger: logging.Logger) -> None:
    def hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.exception("未捕获异常", exc_info=(exc_type, exc_value, exc_tb))
        try:
            dump_dir = paths.logs_dir() / "dumps"
            dump_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            (dump_dir / f"crash-{stamp}.txt").write_text(
                "".join(__import__("traceback").format_exception(exc_type, exc_value, exc_tb)),
                encoding="utf-8",
            )
        except OSError:
            pass

    sys.excepthook = hook


def prepare(level: int = logging.INFO) -> logging.Logger:
    paths.ensure_layout()
    guard_streams()
    logger = setup_logging(level)
    install_excepthook(logger)
    os.environ.setdefault("SHIYIN_LOG_DIR", str(paths.logs_dir()))
    logger.info("启动：数据目录 %s，便携模式 %s", paths.data_dir(), paths.is_portable())
    return logger
