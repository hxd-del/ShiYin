"""诊断"结果为什么比上游终端少"：同一次全源搜索，分别统计「分源原始条数」与「跨源归并后条数」。

用法：python scripts/compare_search.py 晴天
环境中可调：SHIYIN_SEARCH_WORKERS（并发数）、SEARCH_TIMEOUT（预算秒）、PER_SOURCE（每源条数）
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiyin.app import paths
from shiyin.app.adapters import source_catalog
from shiyin.app.adapters.musicdl_adapter import MusicDLAdapter
from shiyin.app.services.search_service import SearchService


def main() -> int:
    keyword = sys.argv[1] if len(sys.argv) > 1 else "晴天"
    size = int(os.environ.get("PER_SOURCE", "10"))
    budget = float(os.environ.get("SEARCH_TIMEOUT", "15"))
    adapter = MusicDLAdapter(paths.cache_dir(), paths.logs_dir(), search_size_per_source=size)
    all_sources = adapter.available_sources()
    defaults = source_catalog.default_enabled_sources()

    started = time.monotonic()
    results, errors = adapter.search(keyword, all_sources, timeout=budget)
    elapsed = int((time.monotonic() - started) * 1000)

    raw_total = sum(len(v) for v in results.values())
    with_url = sum(1 for tracks in results.values() for t in tracks if t.url)
    merged_all = SearchService._merge(results)
    subset = {k: v for k, v in results.items() if k in defaults}
    raw_default = sum(len(v) for v in subset.values())

    print(f"keyword={keyword} sources={len(all_sources)} workers={os.environ.get('SHIYIN_SEARCH_WORKERS', '16')} "
          f"per_source={size} budget={budget} elapsed={elapsed}ms")
    print(f"每源条数: { {k: len(v) for k, v in sorted(results.items())} }")
    print(f"全源 原始={raw_total} 其中带直链={with_url} 去重后={len(merged_all)} 失败={len(errors)}")
    print(f"默认{len(defaults)}源 原始={raw_default} 去重后={len(SearchService._merge(subset))}")
    print(f"合并损失: 全源 {raw_total - len(merged_all)} 条")
    kinds: dict[str, int] = {}
    for msg in errors.values():
        kind = msg.split(":")[0].strip()[:28]
        kinds[kind] = kinds.get(kind, 0) + 1
    print(f"失败类型: {kinds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
