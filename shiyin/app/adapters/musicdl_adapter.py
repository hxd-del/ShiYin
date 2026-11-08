"""musicdl 适配层：唯一允许 import musicdl 的地方。

职责：
1. 只实例化白名单里的音源；
2. 把 SongInfo 映射为 Track，屏蔽上游字段差异；
3. 把上游"打印进度 + 静默异常"的行为收敛成结构化结果与错误。
"""

from __future__ import annotations

import contextlib
import functools
import io
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

from shiyin.app.adapters import source_catalog
from shiyin.app.core.models import Track

# 上游 musicdl 的 requests 调用绝大多数不传 timeout，一个慢源能把线程挂到分钟级。
# 这里统一兜一个默认超时：给慢源足够时间返回结果，同时不至于无限挂起。
# 原版终端不设超时，但 ShiYin 有 41 个源并发，完全不设限会导致界面长时间无响应。
_HTTP_TIMEOUT = 20.0
_TIMEOUT_PATCHED = False


def install_http_timeout(seconds: float = _HTTP_TIMEOUT) -> None:
    global _TIMEOUT_PATCHED
    if _TIMEOUT_PATCHED:
        return
    try:
        import requests
    except ImportError:  # 极端情况下没装 requests，不影响主流程
        return
    original = requests.Session.request

    @functools.wraps(original)
    def request_with_timeout(self, method, url, **kwargs):
        kwargs.setdefault("timeout", seconds)
        return original(self, method, url, **kwargs)

    requests.Session.request = request_with_timeout
    _TIMEOUT_PATCHED = True


class SourceUnavailable(RuntimeError):
    """某个音源在当前环境下不可用（缺依赖、接口失效或被限流）。"""


class MusicDLAdapter:
    def __init__(self, work_dir: str | Path, log_dir: str | Path,
                 search_size_per_source: int = 8, max_retries: int = 3):
        # 上游 LoggerHandle 在 import 时建日志目录，先指到我们自己的 logs 目录
        os.environ.setdefault("SHIYIN_LOG_DIR", str(log_dir))
        install_http_timeout()
        from musicdl.modules import LoggerHandle, MusicClientBuilder

        self._registry = dict(MusicClientBuilder.REGISTERED_MODULES)
        self._logger = LoggerHandle()
        self._work_dir = Path(work_dir)
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._search_size = max(1, int(search_size_per_source))
        # 原版 musicdl 终端固定 search_size_per_page=10，与 search_size_per_source 解耦：
        # 单页源（如 Mitu/HTQYY/Yinyuedao）直接按 search_size_per_page 返回结果，
        # 分页源按 search_size_per_source 累计翻页，page 大一点减少请求次数。
        self._search_size_page = max(self._search_size, 10)
        self._max_retries = max(1, int(max_retries))
        self._clients: dict[str, object] = {}
        self._client_lock = threading.Lock()
        self._devnull = open(os.devnull, "w", encoding="utf-8")
        self._resolve_cache: dict[str, tuple[str, float]] = {}
        self._resolve_lock = threading.Lock()

    # ---------------- 基础信息 ----------------
    def available_sources(self) -> list[str]:
        """白名单 ∩ 上游注册表，缺一不可。"""
        return [name for name in source_catalog.all_sources() if name in self._registry]

    def missing_sources(self) -> list[str]:
        return [name for name in source_catalog.all_sources() if name not in self._registry]

    # ---------------- 客户端构建 ----------------
    def _build_client(self, source: str):
        client_cls = self._registry[source]
        cfg = {
            "search_size_per_source": self._search_size,
            "search_size_per_page": self._search_size_page,
            "strict_limit_search_size_per_page": True,
            "auto_set_proxies": False,
            "random_update_ua": False,
            "maintain_session": True,
            "disable_print": True,
            "max_retries": self._max_retries,
            "logger_handle": self._logger,
            "work_dir": str(self._work_dir / source),
            "default_search_cookies": {},
            "default_download_cookies": {},
            "default_parse_cookies": {},
            "quark_parser_config": {},
            "freeproxy_settings": None,
            "enable_search_curl_cffi": False,
            "enable_parse_curl_cffi": False,
            "enable_download_curl_cffi": False,
        }
        return client_cls(**cfg)

    def client(self, source: str):
        if source not in self._registry:
            raise SourceUnavailable(f"未注册的音源: {source}")
        with self._client_lock:
            if source not in self._clients:
                try:
                    self._clients[source] = self._build_client(source)
                except Exception as err:  # 缺依赖、初始化失败都归到这里
                    raise SourceUnavailable(f"{source} 初始化失败: {type(err).__name__}: {err}") from err
            return self._clients[source]

    # ---------------- 搜索 ----------------
    def search(self, keyword: str, sources: Iterable[str], timeout: float = 25.0,
               proxy: dict[str, str] | None = None, on_source=None,
               ) -> tuple[dict[str, list[Track]], dict[str, str]]:
        """返回 (按源分组的结果, 按源的错误信息)。到点返回已完成的源，不等齐。

        on_source(source, tracks, error) 会在每个源落定时回调一次，界面据此边搜边显示。
        """
        sources = [s for s in sources if s in self._registry]
        results: dict[str, list[Track]] = {}
        errors: dict[str, str] = {}
        if not sources:
            return results, errors

        progress = self._silent_progress()
        request_overrides = {"proxies": proxy} if proxy else {}
        deadline = time.monotonic() + max(3.0, timeout)

        # 注意：ThreadPoolExecutor 的 with 退出会 shutdown(wait=True)，把已超时的慢源
        # 继续等回来（实测能把 25s 超时拖成 57s）。所以手动 shutdown，不等待在跑线程。
        with progress:
            # 源越多越要并发，但并发拉满会让源站更容易限流/超时：实测 16 并发拿到的
            # 结果明显多于 41 并发（43 条 vs 19 条），所以留个上限并允许环境变量覆盖。
            # 41 个源只用 16 并发，加上 15 秒超时，很多源排队还没开始就被砍了。
            # 提到 24 并发 + 放宽超时后，能让更多源在窗口内完成。
            workers = int(os.environ.get("SHIYIN_SEARCH_WORKERS", "24") or 24)
            pool = ThreadPoolExecutor(max_workers=max(1, min(len(sources), workers, 41)))
            futures: dict = {}
            try:
                for source in sources:
                    futures[pool.submit(self._search_one, source, keyword, progress,
                                        request_overrides)] = source
                for future in as_completed(futures, timeout=max(0.0, deadline - time.monotonic())):
                    source = futures[future]
                    try:
                        results[source] = future.result()
                    except Exception as err:
                        errors[source] = self._format_error(err)
                        if on_source:
                            on_source(source, [], errors[source])
                    else:
                        if on_source:
                            on_source(source, results[source], None)
                for future, source in futures.items():
                    if not future.done():
                        errors[source] = "超时未返回"
                        future.cancel()
                        if on_source:
                            on_source(source, [], errors[source])
            except TimeoutError:
                for future, source in futures.items():
                    if not future.done():
                        errors[source] = "超时未返回"
                        future.cancel()
                        if on_source:
                            on_source(source, [], errors[source])
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
        return results, errors

    def _search_one(self, source: str, keyword: str, progress, request_overrides: dict) -> list[Track]:
        client = self.client(source)
        # 原版 musicdl 终端每个源用 5 个搜索线程（base.py search 默认 num_threadings=5），
        # 这里对齐；线程数影响单源内多个分页 URL 的并发抓取。
        songs = client.search(
            keyword=keyword,
            num_threadings=min(5, max(self._search_size, 5)),
            request_overrides=dict(request_overrides),
            rule={},
            main_process_context=progress,
            main_progress_id=None,
            main_progress_lock=None,
        )
        tracks: list[Track] = []
        for song in songs or []:
            track = Track.from_songinfo(song)
            # 有些源搜索阶段不返回直链，点播/下载时再按同源重搜解析（adapter.resolve → refresh），
            # 这里不能因为 url 为空就把结果丢掉，否则列表会比上游终端少一大截。
            if track.ext and track.ext not in _SUPPORTED_EXTS:
                # 上游会把整段 m3u8 当 ext，这里截断成 hls 标记
                track.ext = "m3u8" if "m3u8" in track.ext else track.ext[:5]
            tracks.append(track)
        return tracks

    # ---------------- 直链解析 ----------------
    def resolve(self, track: Track, ttl_seconds: int = 25 * 60) -> str:
        """返回当前有效的直链。优先复用上游刚给的地址，过期或失效时按同源重搜。"""
        if track.url:
            with self._resolve_lock:
                cached = self._resolve_cache.get(track.id)
                if cached and cached[1] > time.monotonic():
                    return cached[0]
            self._remember(track.id, track.url, ttl_seconds)
            return track.url
        return self.refresh(track, ttl_seconds)

    def refresh(self, track: Track, ttl_seconds: int = 25 * 60) -> str:
        """直链失效（403/404）后的重新解析。"""
        if track.source not in self._registry:
            raise SourceUnavailable(f"无法为 {track.source} 重新解析直链")
        keyword = f"{track.title} {track.artist}".strip()
        with self._silent_progress() as progress:
            songs = self.client(track.source).search(
                keyword=keyword,
                num_threadings=2,
                request_overrides={},
                rule={},
                main_process_context=progress,
                main_progress_id=None,
                main_progress_lock=None,
            )
        best = None
        for song in songs or []:
            candidate = Track.from_songinfo(song)
            if not candidate.url:
                continue
            if track.source_id and candidate.source_id == track.source_id:
                best = candidate
                break
            if candidate.title == track.title and (not track.artist or candidate.artist == track.artist):
                best = best or candidate
        if not best:
            raise SourceUnavailable(f"{track.display} 未能在 {track.source} 重新解析到直链")
        self._remember(track.id, best.url, ttl_seconds)
        track.url = best.url
        return best.url

    def _remember(self, track_id: str, url: str, ttl_seconds: int) -> None:
        with self._resolve_lock:
            self._resolve_cache[track_id] = (url, time.monotonic() + ttl_seconds)

    # ---------------- HLS 下载 ----------------
    def download_hls(self, track: Track, dest: str | Path) -> str:
        """HLS 音源交给上游 HLSDownloader 合流，HTTP 音源由下载服务自己处理。"""
        client = self.client(track.source)
        song = track.raw
        if song is None:
            raise SourceUnavailable("缺少上游 SongInfo，无法走 HLS 下载")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        song = _copy_song(song)
        song.work_dir = str(dest.parent)
        song._save_path = str(dest)
        with contextlib.redirect_stdout(self._devnull), contextlib.redirect_stderr(self._devnull):
            downloaded = client.download(song_infos=[song], num_threadings=1,
                                         request_overrides={}, auto_supplement_song=False)
        if not dest.exists():
            raise SourceUnavailable("HLS 下载未产出文件")
        return str(dest)

    # ---------------- 工具 ----------------
    def _silent_progress(self):
        """构造一个不对控制台输出任何内容的 rich Progress。"""
        from rich.console import Console
        from rich.progress import Progress

        return Progress(console=Console(file=self._devnull, force_terminal=False, width=120), transient=True)

    @staticmethod
    def _format_error(err: BaseException) -> str:
        text = f"{type(err).__name__}: {err}".strip()
        return text[:200]

    def close(self) -> None:
        try:
            self._devnull.close()
        except OSError:
            pass


def _copy_song(song):
    import copy

    return copy.deepcopy(song)


_SUPPORTED_EXTS = {
    "mp3", "flac", "wav", "m4a", "aac", "ogg", "opus", "ape", "wv", "tta", "dsf", "dff",
    "wma", "mp4", "m4b", "aiff", "aif", "caf", "amr", "mid", "mka", "webm", "m3u8",
}
