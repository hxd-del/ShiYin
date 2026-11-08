"""按白名单裁剪 upstream musicdl，产出可分发、无 DRM 的 vendor 副本。

用法：
    python scripts/build_whitelist.py            # 生成 shiyin/vendor/musicdl
    python scripts/build_whitelist.py --check    # 只检查已有 vendor 副本

做的事：
1. 复制 musicdl 包，跳过被剔除的音源模块与 wvds 目录；
2. 依据 class 定义重新生成各 sources 子包的 __init__.py 与注册表；
3. 打补丁：SongInfo.with_valid_download_url 不再 import DRM 工具模块；
4. 断言产物中不存在 .wvd、pywidevine、aigpy、ytmusicapi。
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "musicdl"
VENDOR_ROOT = ROOT / "shiyin" / "vendor"
VENDOR = VENDOR_ROOT / "musicdl"
SOURCES_JSON = ROOT / "shiyin" / "sources.json"

SUBPACKAGES = ["sources", "audiobooks", "common", "thirdpartysites"]
SKIP_DIRS = {"__pycache__", "wvds"}
# 仅供 DRM 音源使用的工具模块，连同依赖一起移除
SKIP_UTILS_FILES = {"appleutils.py", "tidalutils.py", "soundcloudutils.py"}

DRM_PATCH_OLD = '''    @property
    def with_valid_download_url(self) -> bool:
        from ..utils.tidalutils import StreamUrl as TidalStreamObj
        from ..utils.appleutils import DownloadItem as AppleStreamObj
        if self.episodes: return all([eps.with_valid_download_url for eps in self.episodes])
        is_valid_download_url_format = self.download_url.startswith('http') if isinstance(self.download_url, str) else isinstance(self.download_url, (TidalStreamObj, AppleStreamObj))
        is_downloadable, with_downloaded_contents = isinstance(self.download_url_status, dict) and self.download_url_status.get('ok'), bool(self.downloaded_contents)
        return bool(with_downloaded_contents or (is_valid_download_url_format and is_downloadable))'''

DRM_PATCH_NEW = '''    @property
    def with_valid_download_url(self) -> bool:
        # patched by shiyin: 不再 import tidalutils/appleutils，从而移除对 pywidevine 的依赖
        if self.episodes: return all([eps.with_valid_download_url for eps in self.episodes])
        if self.downloaded_contents: return True
        is_downloadable = isinstance(self.download_url_status, dict) and bool(self.download_url_status.get('ok'))
        is_valid_download_url_format = isinstance(self.download_url, str) and self.download_url.startswith('http')
        return bool(is_downloadable and is_valid_download_url_format)'''


LOGGER_PATCH_OLD = """    appname, appauthor = 'musicdl', 'zcjin'
    os.makedirs((log_dir := user_log_dir(appname=appname, appauthor=appauthor)), exist_ok=True)
    log_file_path = os.path.join(log_dir, "musicdl.log")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.FileHandler(log_file_path, encoding="utf-8"), logging.StreamHandler()])"""

LOGGER_PATCH_NEW = """    appname, appauthor = 'musicdl', 'zcjin'
    # patched by shiyin: 日志目录可通过 SHIYIN_LOG_DIR 指定，创建失败退化为临时目录，且只写文件不写控制台
    log_dir = os.environ.get('SHIYIN_LOG_DIR') or user_log_dir(appname=appname, appauthor=appauthor)
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        import tempfile
        log_dir = tempfile.mkdtemp(prefix='shiyin-log-')
    log_file_path = os.path.join(log_dir, "musicdl.log")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.FileHandler(log_file_path, encoding="utf-8")])"""


class ClassRef:
    def __init__(self, name: str, module: str):
        self.name = name
        self.module = module


def scan_classes(pkg_dir: Path) -> dict[str, ClassRef]:
    """扫描包内 .py，收集 class 名与所在模块（跳过 __init__ 与 base）。"""
    found: dict[str, ClassRef] = {}
    for py in sorted(pkg_dir.glob("*.py")):
        if py.name in {"__init__.py", "base.py"}:
            continue
        text = py.read_text(encoding="utf-8")
        for m in re.finditer(r"^class\s+([A-Za-z_]\w*)\s*\(", text, re.M):
            name = m.group(1)
            if name.endswith("MusicClient") or name.endswith("Kwargs"):
                found.setdefault(name, ClassRef(name, py.stem))
    return found


def copy_tree(kept_files_by_pkg: dict[str, set[str]]):
    if VENDOR.exists():
        # 直接 rmtree 在 Windows 上偶发 WinError 145（句柄未释放），先改名再异步清理
        trash = VENDOR.with_name(f"musicdl.old-{int(time.time())}")
        VENDOR.rename(trash)
        shutil.rmtree(trash, ignore_errors=True)
    VENDOR.mkdir(parents=True)
    for item in UPSTREAM.rglob("*"):
        rel = item.relative_to(UPSTREAM)
        if not item.is_file():
            continue
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.parts[0] == "modules" and len(rel.parts) > 2 and rel.parts[1] in SUBPACKAGES:
            pkg = rel.parts[1]
            if item.suffix == ".py" and item.name != "__init__.py":
                if item.stem not in kept_files_by_pkg.get(pkg, set()) and item.name != "base.py":
                    continue
        if rel.parts[:2] == ("modules", "utils") and item.name in SKIP_UTILS_FILES:
            continue
        target = VENDOR / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def write_subpackage_inits(kept: dict[str, list[ClassRef]]):
    for pkg, refs in kept.items():
        pkg_dir = VENDOR / "modules" / pkg
        lines = ["'''initialize'''"]
        for ref in refs:
            lines.append(f"from .{ref.module} import {ref.name}")
        (pkg_dir / "__init__.py").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sources_init(refs: list[ClassRef], extra: dict[str, list[ClassRef]]):
    all_refs = sorted(list(refs) + [c for pkg in ("audiobooks", "common", "thirdpartysites") for c in extra[pkg]],
                      key=lambda r: r.name.lower())
    lines = ["'''initialize'''"]
    for ref in refs:
        lines.append(f"from .{ref.module} import {ref.name}")
    lines.append("from .base import BaseMusicClient, BaseMusicClientKwargs")
    lines.append("from ..audiobooks import " + ", ".join(sorted(c.name for c in extra['audiobooks'])))
    lines.append("from ..common import " + ", ".join(sorted(c.name for c in extra['common'])))
    lines.append("from ..thirdpartysites import " + ", ".join(sorted(c.name for c in extra['thirdpartysites'])))
    lines.append("from ..utils import BaseModuleBuilder")
    lines.append("")
    lines.append("")
    lines.append("'''MusicClientBuilder'''")
    lines.append("class MusicClientBuilder(BaseModuleBuilder):")
    lines.append("    REGISTERED_MODULES = {")
    for ref in all_refs:
        lines.append(f"        {ref.name!r}: {ref.name},")
    lines.append("    }")
    lines.append("")
    lines.append("")
    lines.append("'''BuildMusicClient'''")
    lines.append("BuildMusicClient = MusicClientBuilder().build")
    (VENDOR / "modules" / "sources" / "__init__.py").write_text("\n".join(lines) + "\n", encoding="utf-8")


def patch_data_py():
    path = VENDOR / "modules" / "utils" / "data.py"
    text = path.read_text(encoding="utf-8")
    if DRM_PATCH_NEW.strip() in text:
        return
    if DRM_PATCH_OLD not in text:
        raise SystemExit("data.py 结构与预期不符，无法打补丁（上游可能已变化）")
    path.write_text(text.replace(DRM_PATCH_OLD, DRM_PATCH_NEW), encoding="utf-8")


def patch_logger_py():
    path = VENDOR / "modules" / "utils" / "logger.py"
    text = path.read_text(encoding="utf-8")
    if "patched by shiyin" in text:
        return
    if LOGGER_PATCH_OLD not in text:
        raise SystemExit("logger.py 结构与预期不符，无法打补丁")
    path.write_text(text.replace(LOGGER_PATCH_OLD, LOGGER_PATCH_NEW), encoding="utf-8")


def assert_clean():
    bad = []
    for item in VENDOR.rglob("*"):
        if item.suffix == ".wvd":
            bad.append(f"发现 DRM 设备文件: {item}")
        if item.suffix != ".py":
            continue
        text = item.read_text(encoding="utf-8", errors="ignore")
        for token in ("pywidevine", "from aigpy", "import aigpy", "ytmusicapi"):
            if token in text and "shiyin:" not in text.split(token)[0][-200:]:
                bad.append(f"{item.relative_to(VENDOR)} 仍引用 {token}")
    if bad:
        raise SystemExit("裁剪校验失败:\n" + "\n".join(bad))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只校验已有 vendor 副本")
    args = parser.parse_args()

    if args.check:
        if not VENDOR.exists():
            raise SystemExit("vendor 副本不存在，请先执行构建")
        assert_clean()
        print("vendor 副本校验通过")
        return

    cfg = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
    keep_names = set()
    for names in cfg["whitelist"].values():
        keep_names.update(names)
    keep_names.update({"BaseMusicClient", "BaseMusicClientKwargs"})

    global keep_by_pkg
    keep_by_pkg = {}
    kept_files_by_pkg = {}
    classmap: dict[str, ClassRef] = {}

    for pkg in SUBPACKAGES:
        refs = scan_classes(UPSTREAM / "modules" / pkg)
        classmap.update(refs)
        keep = [r for n, r in refs.items() if n in keep_names]
        keep_by_pkg[pkg] = sorted(keep, key=lambda r: r.name.lower())
        kept_files_by_pkg[pkg] = {r.module for r in keep}

    missing = sorted(n for n in keep_names if n not in classmap and n not in {"BaseMusicClient", "BaseMusicClientKwargs"})
    if missing:
        raise SystemExit("白名单中的类在上游找不到: " + ", ".join(missing))

    copy_tree(kept_files_by_pkg)
    write_subpackage_inits({pkg: keep_by_pkg[pkg] for pkg in ["audiobooks", "common", "thirdpartysites"]})
    write_sources_init(keep_by_pkg["sources"], keep_by_pkg)
    patch_data_py()
    patch_logger_py()
    assert_clean()

    total = sum(1 for _ in VENDOR.rglob("*.py"))
    print(f"vendor 构建完成：{VENDOR}")
    print(f"保留音源 {len(keep_names) - 2} 个，Python 文件 {total} 个")


if __name__ == "__main__":
    sys.exit(main())
