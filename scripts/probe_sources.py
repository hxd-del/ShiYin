"""逐个音源单独试搜，输出每个源的耗时、条数与错误，用于判断是源挂了还是并发被限流。"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiyin.app import paths
from shiyin.app.adapters import source_catalog
from shiyin.app.adapters.musicdl_adapter import MusicDLAdapter


def main() -> int:
    keyword = sys.argv[1] if len(sys.argv) > 1 else "晴天"
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else source_catalog.default_enabled_sources()

    adapter = MusicDLAdapter(paths.cache_dir(), paths.logs_dir())
    for name in names:
        started = time.monotonic()
        results, errors = adapter.search(keyword, [name], timeout=12.0)
        elapsed = int((time.monotonic() - started) * 1000)
        tracks = results.get(name) or []
        error = errors.get(name, "")
        print(f"{name}\t{len(tracks)}\t{elapsed}ms\t{error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
