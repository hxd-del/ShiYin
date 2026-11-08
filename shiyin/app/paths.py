"""路径解析：安装版写用户目录，便携版写程序目录。

便携模式通过程序目录下的 portable.flag 判定，符合设计文档 4.2 的口径。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PORTABLE_FLAG = "portable.flag"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """程序所在目录；源码运行时是仓库根目录。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def is_portable() -> bool:
    return (app_root() / PORTABLE_FLAG).exists()


def data_dir() -> Path:
    """数据根目录。SHIYIN_DATA_DIR 可强制指定（自检/多实例调试用）。"""
    override = os.environ.get("SHIYIN_DATA_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    if is_portable():
        return app_root() / "data"
    base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / ".local")) / "ShiYin"
    try:
        base.mkdir(parents=True, exist_ok=True)
        probe = base / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return base
    except OSError:
        fallback = app_root() / "data"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _sub(name: str) -> Path:
    path = data_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "library.db"


def config_path() -> Path:
    return data_dir() / "config.json"


def library_dir() -> Path:
    return _sub("library")


def cache_dir() -> Path:
    return _sub("cache")


def covers_dir() -> Path:
    return _sub("covers")


def logs_dir() -> Path:
    return _sub("logs")


def search_work_dir() -> Path:
    return _sub("search")


def startup_log_path() -> Path:
    return logs_dir() / "shiyin.log"


def ensure_layout() -> None:
    for fn in (library_dir, cache_dir, covers_dir, logs_dir, search_work_dir):
        fn()


def temp_dir() -> Path:
    return Path(tempfile.gettempdir())
