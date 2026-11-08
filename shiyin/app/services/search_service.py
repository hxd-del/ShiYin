"""搜索服务：并发编排、跨源归并、源健康统计。

不依赖 Qt，可以在测试里直接调用。
"""

from __future__ import annotations

import time
from typing import Iterable

from shiyin.app.adapters.musicdl_adapter import MusicDLAdapter
from shiyin.app.core.models import SearchResult, Track


class SearchService:
    def __init__(self, adapter: MusicDLAdapter, limit_per_source: int = 5, timeout: float = 20.0,
                 repository=None, proxy: dict[str, str] | None = None,
                 merge_same_song: bool = False):
        self.adapter = adapter
        self.limit_per_source = limit_per_source
        self.timeout = timeout
        self.repository = repository
        self.proxy = proxy or {}
        # 默认不做跨源合并：同一首歌在不同源各占一行，条数与上游终端一致，
        # 由用户自己挑来源（合并后同曲只剩音质最高的一条，其余藏进 alternatives）。
        self.merge_same_song = merge_same_song

    def search(self, keyword: str, sources: Iterable[str] | None = None,
               expanded_keywords: Iterable[str] | None = None, on_partial=None) -> SearchResult:
        keyword = (keyword or "").strip()
        started = time.monotonic()
        if not keyword:
            return SearchResult(keyword="")

        sources = list(sources or self.adapter.available_sources())
        raw: dict[str, list[Track]] = {}
        errors: dict[str, str] = {}
        done_sources = 0

        def handle(source: str, tracks: list[Track], error: str | None) -> None:
            """每落定一个源就推一次已归并的结果，界面不用等到齐。"""
            nonlocal done_sources
            done_sources += 1
            if error:
                errors[source] = error
            if tracks:
                raw[source] = tracks
            if on_partial:
                on_partial(self._merge(raw, self.merge_same_song), dict(errors), done_sources, len(sources))

        for kw in ([keyword] + [k for k in (expanded_keywords or []) if k and k != keyword]):
            done_sources = 0
            results, errs = self.adapter.search(kw, sources, timeout=self.timeout,
                                                proxy=self.proxy, on_source=handle)
            for source, tracks in results.items():
                raw.setdefault(source, []).extend(tracks)
            errors.update(errs)
            if raw:
                break

        self._update_health(raw, errors)
        items = self._merge(raw, self.merge_same_song)
        return SearchResult(
            keyword=keyword,
            items=items,
            per_source={src: len(tracks) for src, tracks in raw.items()},
            errors=errors,
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )

    def _update_health(self, raw: dict[str, list[Track]], errors: dict[str, str]) -> None:
        if self.repository is None:
            return
        for source in raw:
            if raw[source]:
                self.repository.record_source_ok(source)
            else:
                self.repository.record_source_fail(source)
        for source in errors:
            self.repository.record_source_fail(source)

    @staticmethod
    def _merge(raw: dict[str, list[Track]], merge_same_song: bool = True) -> list[Track]:
        """默认按源内标识去重，各源结果都保留；开启合并时再按归一化三元组跨源归并。"""
        merged: dict[tuple, Track] = {}
        for source, tracks in raw.items():
            for track in tracks:
                if merge_same_song:
                    key: tuple = ("song",) + track.merge_key
                else:
                    # 只做同源去重：不同源的同名曲目各占一行；同一源里同名但格式/大小不同的
                    # 版本（FLAC 与 MP3）也要留着，否则单源 10 条会被砍到 2~5 条。
                    key = ("src", source, track.source_id or
                           f"{track.title}|{track.artist}|{track.ext}|{track.size_bytes}|{track.bitrate}")
                current = merged.get(key)
                if current is None:
                    merged[key] = track
                    continue
                if track.quality_score > current.quality_score:
                    track.alternatives = [current] + current.alternatives
                    merged[key] = track
                elif track.source != current.source or track.source_id != current.source_id:
                    current.alternatives.append(track)
        items = list(merged.values())
        items.sort(key=lambda t: (-t.quality_score, t.title))
        return items
