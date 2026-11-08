"""组装根：把配置、数据库、适配层、服务层拼成一个可用的上下文。

界面只依赖这里暴露的对象，不自己 new 服务，避免 UI 与实现耦合。
"""

from __future__ import annotations

import logging
import os
import sqlite3
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from shiyin.app import paths
from shiyin.app.adapters.musicdl_adapter import MusicDLAdapter
from shiyin.app.core.audio_backend import AudioBackend
from shiyin.app.core.stream_cache import StreamCache
from shiyin.app.data import db
from shiyin.app.data.repository import Repository
from shiyin.app.services.download_service import DownloadService
from shiyin.app.services.library_service import LibraryService
from shiyin.app.services.playback_service import PlaybackService
from shiyin.app.services.search_service import SearchService
from shiyin.app.services.settings_service import SettingsService


def _db_track_count(path: Path) -> int:
    if not path.exists():
        return 0
    conn = None
    try:
        conn = sqlite3.connect(str(path), timeout=5)
        row = conn.execute(
            "SELECT COUNT(*) FROM tracks WHERE is_deleted = 0 AND path IS NOT NULL",
        ).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.DatabaseError:
        return 0
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _db_meta(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    conn = None
    try:
        conn = sqlite3.connect(str(path), timeout=5)
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None
    except sqlite3.DatabaseError:
        return None
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _sqlite_copy(src: Path, dst: Path) -> None:
    """用 SQLite 备份 API 复制，避免只拷主文件漏掉 WAL 里的最新写入。"""
    source = sqlite3.connect(str(src), timeout=10)
    target = sqlite3.connect(str(dst), timeout=10)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def _restore_legacy_db(canonical: Path, legacy: Path) -> bool:
    """只在 canonical 为空时恢复源码根旧库；两份库都先备份。

    这是给源码运行/旧版本升级用的一次性保险，打包版通常找不到项目根旧库，
    找不到就自然跳过，不阻塞启动。
    """
    logger = logging.getLogger("shiyin")
    if not legacy.exists() or legacy.resolve() == canonical.resolve():
        return False
    legacy_count = _db_track_count(legacy)
    if legacy_count <= 0:
        return False
    if _db_meta(canonical, "legacy_import_v1"):
        logger.info("旧库恢复已执行过，跳过：%s", legacy)
        return False
    canonical_count = _db_track_count(canonical)
    if canonical_count > 0:
        logger.info("当前库已有 %d 首，不覆盖；旧库 %s 有 %d 首", canonical_count, legacy, legacy_count)
        return False

    stamp = time.strftime("%Y%m%d-%H%M%S")
    try:
        canonical.parent.mkdir(parents=True, exist_ok=True)
        if canonical.exists():
            backup = canonical.with_name(f"library.db.bak-{stamp}")
            shutil.copy2(canonical, backup)
            logger.info("已备份空/旧 canonical 库：%s", backup)
        legacy_backup = legacy.with_name(f"library.db.legacy-bak-{stamp}")
        _sqlite_copy(legacy, legacy_backup)
        logger.info("已备份源码根旧库：%s", legacy_backup)

        tmp = canonical.with_name("library.db.restore-tmp")
        if tmp.exists():
            tmp.unlink()
        _sqlite_copy(legacy, tmp)
        os.replace(tmp, canonical)
        logger.info("已从旧库恢复 %d 首到 %s", legacy_count, canonical)
        return True
    except Exception as err:
        logger.warning("旧库恢复失败（继续使用空库）：%s", err)
        try:
            tmp = canonical.with_name("library.db.restore-tmp")
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return False


@dataclass
class AppContext:
    settings: SettingsService
    repository: Repository
    adapter: MusicDLAdapter
    stream_cache: StreamCache
    search: SearchService
    downloads: DownloadService
    library: LibraryService
    backend: AudioBackend
    playback: PlaybackService
    db_path: Path

    def close(self) -> None:
        try:
            self.stream_cache.stop()
        except Exception:
            pass


def build_context(data_dir: Path | None = None, start_cache: bool = True) -> AppContext:
    data_dir = data_dir or paths.data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    settings = SettingsService(data_dir / "config.json")

    db_path = data_dir / "library.db"
    # 只在真正的默认数据目录做旧库搬家；UI 冒烟/测试探针的临时库不能被塞进项目根旧库。
    allow_legacy_restore = (
        not os.environ.get("SHIYIN_DATA_DIR")
        and data_dir.resolve() == paths.data_dir().resolve()
    )
    restored = False
    if allow_legacy_restore:
        restored = _restore_legacy_db(db_path, paths.app_root() / "data" / "library.db")
    logging.getLogger("shiyin").info("数据目录：%s；数据库：%s", data_dir, db_path)
    conn = db.connect(db_path)
    db.init_db(conn)
    repository = Repository(conn)
    repository.ensure_default_playlists()
    if restored:
        repository.set_meta("legacy_import_v1", str(int(time.time())))

    adapter = MusicDLAdapter(
        work_dir=paths.search_work_dir(),
        log_dir=paths.logs_dir(),
        search_size_per_source=int(settings.get("search_size_per_source") or 5),
        max_retries=3,
    )

    cache = StreamCache(
        root=paths.cache_dir(),
        limit_bytes=int(settings.get("cache_limit_mb") or 2048) * 1024 * 1024,
        ttl_seconds=int(settings.get("stream_ttl_minutes") or 25) * 60,
        resolver=adapter.refresh,
    )
    if start_cache:
        cache.start()

    search = SearchService(
        adapter,
        limit_per_source=int(settings.get("search_size_per_source") or 5),
        # 上游终端不设超时，慢源最终都会返回；这里给 20 秒预算，多数源能落地，
        # 同时界面是流式的，用户不用等满就已有结果。上限 30 秒，避免设置被填成离谱值。
        timeout=min(float(settings.get("search_timeout_seconds") or 20), 60.0),
        repository=repository,
        proxy=settings.proxy,
        merge_same_song=bool(settings.get("merge_same_song")),
    )
    downloads = DownloadService(
        adapter, settings, repository, stream_cache=cache,
        download_dir=settings.get("download_dir") or paths.library_dir(),
    )
    library = LibraryService(repository, covers_dir=paths.covers_dir())
    backend = AudioBackend()
    playback = PlaybackService(backend, cache, settings=settings, repository=repository, adapter=adapter)

    return AppContext(
        settings=settings,
        repository=repository,
        adapter=adapter,
        stream_cache=cache,
        search=search,
        downloads=downloads,
        library=library,
        backend=backend,
        playback=playback,
        db_path=db_path,
    )
