"""校验便携包：解压 → 确认 portable.flag → 在干净环境里 --selftest → 检查数据落在程序目录。"""

import os
import subprocess
import sys
from pathlib import Path

import py7zr

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "dist" / "ShiYin-Portable-0.1.0.7z"
TARGET = ROOT / "build" / "portable-test"


def main() -> int:
    with py7zr.SevenZipFile(ARCHIVE) as zip_file:
        names = zip_file.getnames()
        print(f"归档条目: {len(names)}")
        flag = [n for n in names if n.endswith("portable.flag")]
        print(f"portable.flag: {flag}")
        zip_file.extractall(TARGET)

    app_dir = TARGET / "ShiYin-0.1.0"
    env = {k: v for k, v in os.environ.items() if k != "SHIYIN_DATA_DIR"}
    result = subprocess.run([str(app_dir / "ShiYin.exe"), "--selftest"], cwd=str(app_dir),
                            env=env, capture_output=True, timeout=180)
    print(f"selftest exit={result.returncode}")
    data_dir = app_dir / "data"
    for name in ("config.json", "library.db", "shiyin.log"):
        found = list(data_dir.rglob(name))
        print(f"  {name}: {[str(p.relative_to(app_dir)) for p in found]}")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
