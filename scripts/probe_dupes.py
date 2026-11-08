"""看单个音源返回的原始条目里有多少是重复的（决定要不要在界面上做同源去重）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiyin.app import paths
from shiyin.app.adapters.musicdl_adapter import MusicDLAdapter

SOURCE = sys.argv[1] if len(sys.argv) > 1 else "BodianMusicClient"
KEYWORD = sys.argv[2] if len(sys.argv) > 2 else "晴天"

adapter = MusicDLAdapter(paths.cache_dir(), paths.logs_dir(), search_size_per_source=10)
client = adapter.client(SOURCE)
progress = adapter._silent_progress()
with progress:
    songs = client.search(keyword=KEYWORD, num_threadings=4, request_overrides={}, rule={},
                          main_process_context=progress, main_progress_id=None,
                          main_progress_lock=None)
print(f"source={SOURCE} keyword={KEYWORD} songs={len(songs or [])}")
for idx, song in enumerate(songs or []):
    print(idx,
          "|", getattr(song, "song_name", ""),
          "|", getattr(song, "singers", ""),
          "|", getattr(song, "ext", ""),
          "|size", getattr(song, "file_size_bytes", 0),
          "|br", getattr(song, "bitrate", 0),
          "|id", str(getattr(song, "identifier", ""))[:16],
          "|url", str(getattr(song, "download_url", ""))[:40])
