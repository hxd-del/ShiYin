"""音源白名单：从 shiyin/sources.json 读取，避免代码里散落字符串。

sources.json 同时被 scripts/build_whitelist.py 使用，保证"打进去的"与"能选的"一致。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_JSON_PATH = Path(__file__).resolve().parents[2] / "sources.json"

GROUP_LABELS = {
    "mainland": "大陆主流",
    "aggregator": "聚合网关",
    "radio": "音频电台",
    "scraper": "抓取站点",
}


@lru_cache(maxsize=1)
def catalog() -> dict:
    return json.loads(_JSON_PATH.read_text(encoding="utf-8"))


def groups() -> dict[str, list[str]]:
    return {key: list(value) for key, value in catalog().get("whitelist", {}).items()}


def all_sources() -> list[str]:
    result: list[str] = []
    for names in catalog().get("whitelist", {}).values():
        for name in names:
            if name not in result:
                result.append(name)
    return result


def default_enabled_sources() -> list[str]:
    return list(catalog().get("enabled_default", []))


def excluded_sources() -> list[str]:
    return list(catalog().get("excluded", []))


def source_label(name: str) -> str:
    """QQMusicClient -> QQ。"""
    return name.removesuffix("MusicClient")
