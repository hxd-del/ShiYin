"""核查 sqlite 在不同目录下的可写性，用来区分"沙箱拦截"与"代码问题"。"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiyin.app.data import db  # noqa: E402


def probe(label: str, path: Path) -> None:
    try:
        conn = db.connect(path)
        conn.execute("CREATE TABLE IF NOT EXISTS t(a INTEGER)")
        conn.execute("INSERT INTO t VALUES(1)")
        conn.commit()
        print(f"[OK] {label}: {path} rows={conn.execute('SELECT COUNT(*) FROM t').fetchone()[0]} "
              f"journal={conn.execute('PRAGMA journal_mode').fetchone()[0]}")
        conn.close()
    except Exception as err:
        print(f"[FAIL] {label}: {path} -> {type(err).__name__}: {err}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    probe("project build", root / "build" / "dbprobe" / "a.db")
    probe("project root", root / "dbprobe_root.db")
    probe("temp", Path(tempfile.mkdtemp(prefix="shiyin-db-")) / "a.db")
    local = Path.home() / "AppData" / "Local" / "ShiYinProbe"
    probe("localappdata", local / "a.db")


if __name__ == "__main__":
    main()
