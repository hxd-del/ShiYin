"""联调冒烟：真实音源搜索 → 直链 → 流缓存。

运行：.venv\\Scripts\\python.exe scripts\\smoke_search.py 晴天
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shiyin.app.adapters.musicdl_adapter import MusicDLAdapter  # noqa: E402
from shiyin.app.core.stream_cache import StreamCache  # noqa: E402
from shiyin.app.services.search_service import SearchService  # noqa: E402

SOURCES = ["NeteaseMusicClient", "QQMusicClient", "KuwoMusicClient"]


def main() -> None:
    keyword = sys.argv[1] if len(sys.argv) > 1 else "晴天"
    work = Path("build/smoke-search")
    adapter = MusicDLAdapter(work_dir=work / "work", log_dir=work / "logs", search_size_per_source=5)
    print("可用音源:", len(adapter.available_sources()))

    service = SearchService(adapter, timeout=20)
    result = service.search(keyword, SOURCES)
    print(f"关键词 {keyword}: {result.summary}, {result.elapsed_ms} ms")
    for source, count in result.per_source.items():
        print("  ", source, count)
    for source, err in result.errors.items():
        print("  ERR", source, err)
    for item in result.items[:5]:
        print("  -", item.source, item.title, item.artist, item.quality_text, item.protocol, len(item.alternatives))

    if not result.items:
        raise SystemExit("没有搜索结果，检查网络或音源可用性")

    pick = result.items[0]
    cache = StreamCache(work / "cache", resolver=adapter.refresh)
    cache.start()
    entry, url = cache.register(pick)
    for _ in range(100):
        if entry.done or entry.error:
            break
        time.sleep(0.2)
    print("流缓存:", "ok" if entry.done else "fail", entry.downloaded, entry.total, entry.error, url)

    import requests

    resp = requests.get(url, headers={"Range": "bytes=0-1023"}, timeout=10)
    print("HTTP:", resp.status_code, len(resp.content), "B, magic:", resp.content[:4].hex())
    cache.stop()
    adapter.close()


if __name__ == "__main__":
    main()
