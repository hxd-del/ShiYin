"""不依赖 7-Zip 的便携包生成（纯 Python，py7zr）。

用法：.venv\\Scripts\\python.exe packaging\\make_portable.py [版本号]
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

import py7zr

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from shiyin import __version__

    version = sys.argv[1] if len(sys.argv) > 1 else __version__
    src = ROOT / "dist" / "ShiYin"
    if not src.exists():
        print("找不到 dist\\ShiYin，请先跑 PyInstaller")
        return 1

    staging = ROOT / "dist" / "portable" / f"ShiYin-{version}"
    if staging.exists():
        staging = staging.with_name(f"{staging.name}-{datetime.now():%H%M%S}")

    def ignore(directory: str, names: list[str]) -> list[str]:
        # 只剔除顶层的运行时数据；shutil.ignore_patterns 按 basename 匹配，
        # 会把 _internal\fake_useragent\data 这类库数据一起误删，导致便携版所有音源初始化失败。
        if Path(directory) == src:
            return [n for n in names if n in ("data", "logs")]
        return []

    shutil.copytree(src, staging, ignore=ignore)
    (staging / "portable.flag").write_text("ShiYin portable", encoding="ascii")

    archive = ROOT / "dist" / f"ShiYin-Portable-{version}.7z"
    if archive.exists():
        archive.unlink()
    with py7zr.SevenZipFile(archive, "w", filters=[{"id": py7zr.FILTER_LZMA2, "preset": 9}]) as zip_file:
        zip_file.writeall(staging, arcname=f"ShiYin-{version}")
    size_mb = archive.stat().st_size / 1024 / 1024
    print(f"便携包: {archive} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
