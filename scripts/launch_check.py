"""打包产物启动检查：跑一次 --selftest，确认进程能正常退出并落盘数据。

用法：.venv\\Scripts\\python.exe scripts\\launch_check.py [exe路径] [数据目录]
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

EXE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/ShiYin/ShiYin.exe")
DATA = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("build/launch-check")


def main() -> int:
    env = dict(os.environ)
    env["SHIYIN_DATA_DIR"] = str(DATA.resolve())
    env.pop("QT_QPA_PLATFORM", None)
    proc = subprocess.run([str(EXE.resolve()), "--selftest"], cwd=str(EXE.resolve().parent),
                          env=env, timeout=60, capture_output=True)
    print("exit:", proc.returncode)
    if proc.stdout:
        print("stdout:", proc.stdout.decode("utf-8", "ignore")[:400])
    if proc.stderr:
        print("stderr:", proc.stderr.decode("utf-8", "ignore")[:800])
    if not DATA.exists():
        print("数据目录未创建")
        return 1
    for path in sorted(DATA.rglob("*")):
        if path.is_file():
            print(" file", path.relative_to(DATA), path.stat().st_size, "B")
    log = DATA / "logs" / "shiyin.log"
    if log.exists():
        print("--- 日志尾部")
        print("\n".join(log.read_text(encoding="utf-8", errors="ignore").splitlines()[-10:]))
    return 0 if proc.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
