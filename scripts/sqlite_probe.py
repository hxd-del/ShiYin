"""诊断脚本：在 PyInstaller 产物里逐个 journal 模式检查建表/插入是否真的生效。"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path


def run_mode(base: Path, mode: str) -> None:
    path = base / f"t_{mode.lower()}.db"
    print(f"--- mode={mode} db={path}")
    conn = sqlite3.connect(str(path), timeout=5)
    for sql in (f"PRAGMA journal_mode={mode}", "CREATE TABLE probe_t(a INTEGER)",
                "INSERT INTO probe_t VALUES(1)", "SELECT COUNT(*) FROM probe_t"):
        try:
            cur = conn.execute(sql)
            rows = cur.fetchall() if sql.startswith(("SELECT", "PRAGMA")) else []
            print(f"  ok   {sql} -> {rows[:3]}")
        except Exception as err:  # noqa: BLE001
            print(f"  FAIL {sql} -> {type(err).__name__}: {err}")
    conn.commit()
    conn.close()
    print("  file:", path.stat().st_size if path.exists() else "missing",
          "siblings:", [p.name for p in path.parent.iterdir() if p.name.startswith(path.name)])


def main() -> None:
    print("frozen:", getattr(sys, "frozen", False), "tmp:", tempfile.gettempdir(), "cwd:", os.getcwd())
    base = Path(tempfile.mkdtemp(prefix="sqlprobe-"))
    for mode in ("WAL", "MEMORY", "DELETE", "OFF", "TRUNCATE", "PERSIST"):
        run_mode(base, mode)
    print("files:", sorted(p.name + f"({p.stat().st_size})" for p in base.iterdir()))


if __name__ == "__main__":
    main()
