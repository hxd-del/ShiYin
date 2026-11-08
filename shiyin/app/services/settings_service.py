"""配置读写。

JSON 单文件、原子替换；键值全部有默认值，缺字段不会导致启动失败。
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from shiyin.app import paths
from shiyin.app.adapters.source_catalog import default_enabled_sources

# 上一版的默认音源集（10 个大陆源）。老 config 里若正好是这一串，说明是当年程序自动写的，
# 升级后应当作“未设置”处理，回落到 sources.json 里的全源默认。
_LEGACY_DEFAULT_SOURCES = [
    "QianqianMusicClient", "BodianMusicClient", "KuwoMusicClient", "MiguMusicClient",
    "QQMusicClient", "KugouMusicClient", "NeteaseMusicClient", "SodaMusicClient",
    "FiveSingMusicClient", "BilibiliMusicClient",
]

# 曾经全开过 36 源的 config，回落到 10 个稳定源
_FULL_SOURCES_SET = [
    "QQMusicClient", "NeteaseMusicClient", "KugouMusicClient", "KuwoMusicClient",
    "MiguMusicClient", "QianqianMusicClient", "SodaMusicClient", "BilibiliMusicClient",
    "BodianMusicClient", "FiveSingMusicClient", "StreetVoiceMusicClient", "MOOVMusicClient",
    "GDStudioMusicClient", "JBSouMusicClient", "TuneHubMusicClient", "XiaoBaiMusicClient",
    "MyFreeMP3MusicClient", "XimalayaMusicClient", "LizhiMusicClient", "QingtingMusicClient",
    "LRTSMusicClient", "ITunesMusicClient", "MituMusicClient", "BuguyyMusicClient",
    "GequbaoMusicClient", "YinyuedaoMusicClient", "FangpiMusicClient", "GequhaiMusicClient",
    "HTQYYMusicClient", "TwoT58MusicClient", "YinyuekuMusicClient", "GequkeMusicClient",
    "MGMP3MusicClient", "LeedodoMusicClient", "SgogoMusicClient", "XMFWAVMusicClient",
]

DEFAULTS: dict[str, Any] = {
    "download_dir": "",
    "library_dir": "",
    "concurrency": 6,
    "per_source_concurrency": 3,
    "cache_limit_mb": 2048,
    "stream_ttl_minutes": 25,
    "search_size_per_source": 5,
    "search_timeout_seconds": 20,
    "merge_same_song": False,
    "enabled_sources": None,  # None 表示使用内置默认
    "theme": "light",
    "volume": 0.8,
    "repeat_mode": "off",
    "minimize_to_tray": True,
    "close_to_tray_hint_shown": False,
    "startup_restore_enabled": True,
    "resume_autoplay": False,
    "startup_scan_enabled": True,
    "proxy": "",
    "first_run": True,
}


class SettingsService:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else paths.config_path()
        self._data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self._apply_default_paths()
            self.save()
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = {}
        logging.getLogger("shiyin").debug("加载配置 %s", self.path)
        self._data.update({k: v for k, v in raw.items() if k in DEFAULTS})
        # 确保 theme 值有效
        if self._data.get("theme") not in ("light", "dark"):
            self._data["theme"] = "light"
        self._apply_default_paths()
        self._migrate_sources()

    def _apply_default_paths(self) -> None:
        """路径自愈：便携包被解压到别处后，config 里仍是旧机器的绝对路径，要重置。"""
        for key in ("download_dir", "library_dir"):
            value = self._data.get(key)
            if not value or not self._path_usable(value):
                self._data[key] = str(paths.library_dir())

    def _migrate_sources(self) -> None:
        """旧版本把默认 10 源或全开 36 源写进了 config；这些都不是用户主选，
    
        升级到“10 个稳定源”后要清掉它，回落到 sources.json 的默认。
        """
        value = self._data.get("enabled_sources")
        if isinstance(value, list):
            if sorted(value) == sorted(_LEGACY_DEFAULT_SOURCES) or sorted(value) == sorted(_FULL_SOURCES_SET):
                self._data["enabled_sources"] = None

    @staticmethod
    def _path_usable(value: str) -> bool:
        try:
            path = Path(value)
            root = paths.data_dir().resolve()
            resolved = path.resolve()
        except (OSError, ValueError):
            return False
        # 数据目录内的路径总是可用；目录外的只有在真实存在时才算用户自选
        if root in resolved.parents or resolved == root:
            return True
        return resolved.exists()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        payload = json.dumps(self._data, ensure_ascii=False, indent=2)
        # 音量、进度等交互会高频触发保存，Windows 上目标文件被瞬时占用时
        # os.replace 会抛 WinError 5。这里重试几次并吞掉异常：配置丢了可以重设，
        # 抛进 Qt 槽里只会刷一堆崩溃日志。
        last_error: OSError | None = None
        for attempt in range(4):
            try:
                tmp.write_text(payload, encoding="utf-8")
                os.replace(tmp, self.path)
                return
            except OSError as err:
                last_error = err
                time.sleep(0.03 * (attempt + 1))
        logging.getLogger("shiyin").warning("配置写入失败：%s", last_error)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any, *, save: bool = True) -> None:
        self._data[key] = value
        if save:
            self.save()

    def update(self, values: dict[str, Any]) -> None:
        self._data.update(values)
        self.save()

    @property
    def enabled_sources(self) -> list[str]:
        value = self._data.get("enabled_sources")
        if not value:
            return default_enabled_sources()
        return list(value)

    def set_enabled_sources(self, names: list[str]) -> None:
        self.set("enabled_sources", list(names))

    @property
    def proxy(self) -> dict[str, str]:
        raw = (self._data.get("proxy") or "").strip()
        return {"http": raw, "https": raw} if raw else {}
