"""服务层冒烟测试：不依赖 Qt，用一个本地 HTTP 假源验证下载/缓存链路。

运行：.venv\\Scripts\\python.exe scripts\\smoke_services.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shiyin.app.core.models import Track, SearchResult  # noqa: E402
from shiyin.app.core.stream_cache import StreamCache  # noqa: E402
from shiyin.app.data import db  # noqa: E402
from shiyin.app.data.repository import Repository  # noqa: E402
from shiyin.app.services.settings_service import SettingsService  # noqa: E402

PAYLOAD = bytes(range(256)) * 512  # 128 KB


class FakeSource(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        rng = self.headers.get("Range")
        data = PAYLOAD
        start, end = 0, len(data) - 1
        if rng:
            part = rng.split("=")[1].split("-")
            start = int(part[0])
            end = int(part[1]) if len(part) > 1 and part[1] else end
        chunk = data[start:end + 1]
        self.send_response(206 if rng else 200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(chunk)))
        if rng:
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
        self.end_headers()
        self.wfile.write(chunk)


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"[{'OK' if condition else 'FAIL'}] {name} {detail}")
    if not condition:
        raise SystemExit(1)


def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="shiyin-smoke-"))
    print("work dir:", work)

    settings = SettingsService(work / "config.json")
    check("settings defaults", settings.get("concurrency") == 6, str(settings.get("download_dir")))
    settings.update({"download_dir": str(work / "downloads"), "library_dir": str(work / "library")})

    conn = db.connect(work / "library.db")
    db.init_db(conn)
    repo = Repository(conn)
    repo.ensure_default_playlists()
    track = Track(title="测试曲目", artist="测试歌手", source="local", source_id="smoke-1",
                  ext="mp3", bitrate=320, size_bytes=len(PAYLOAD), duration_ms=180000)
    repo.upsert_track(track, fingerprint="fp-smoke")
    check("repository insert/list", repo.count_tracks() == 1)
    check("model id/quality", track.id.startswith("local:") or len(track.id) == 16,
          f"{track.id} / {track.quality_text} / {track.duration_text}")

    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSource)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    cache = StreamCache(work / "cache", limit_bytes=8 * 1024 * 1024, ttl_seconds=600)
    cache.start()
    remote = Track(title="远程曲目", artist="远程歌手", source="QQMusicClient", source_id="smoke-2",
                   ext="mp3", url=f"http://127.0.0.1:{port}/fake.mp3", duration_ms=120000)
    entry, local_url = cache.register(remote)
    for _ in range(60):
        if entry.done:
            break
        time.sleep(0.2)
    check("stream cache complete", entry.done, f"{entry.downloaded}/{entry.total} -> {local_url}")

    import requests

    head = requests.get(local_url, headers={"Range": "bytes=100-199"}, timeout=10)
    check("stream range", head.status_code == 206 and len(head.content) == 100,
          f"{head.status_code} {len(head.content)}B")
    full = requests.get(local_url, timeout=10)
    check("stream full", full.status_code == 200 and len(full.content) == len(PAYLOAD))

    # 下载服务：直链走 HTTP，验证落盘与入库
    from shiyin.app.services.download_service import DownloadService

    class _Adapter:
        def resolve(self, track):
            return track.url

        def download_hls(self, track, dest):
            raise NotImplementedError

    downloads = DownloadService(_Adapter(), settings, repo, stream_cache=cache,
                                download_dir=work / "downloads")
    task_id = downloads.submit(remote)
    for _ in range(100):
        snap = {t.task_id: t for t in downloads.snapshot()}[task_id]
        if snap.status in ("done", "failed", "cancelled"):
            break
        time.sleep(0.2)
    check("download done", snap.status == "done", f"{snap.status} {snap.error}")
    check("download file", bool(snap.dest_path) and Path(snap.dest_path).stat().st_size == len(PAYLOAD))
    check("download registered", repo.count_tracks() >= 2)

    cache.stop()
    server.shutdown()
    print("\n服务层冒烟通过")


if __name__ == "__main__":
    main()
