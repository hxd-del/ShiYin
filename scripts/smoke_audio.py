"""音频后端冒烟：用标准库生成一段 wav，验证 QtMultimedia 能加载、播放、拖动。"""

from __future__ import annotations

import math
import os
import struct
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402

from shiyin.app.core.audio_backend import AudioBackend  # noqa: E402


def make_wav(path: Path, seconds: int = 3) -> None:
    rate = 22050
    with wave.open(str(path), "wb") as fp:
        fp.setnchannels(1)
        fp.setsampwidth(2)
        fp.setframerate(rate)
        for n in range(rate * seconds):
            value = int(12000 * math.sin(2 * math.pi * 440 * n / rate))
            fp.writeframes(struct.pack("<h", value))


def main() -> None:
    app = QCoreApplication(sys.argv)
    path = Path(tempfile.mkdtemp(prefix="shiyin-audio-")) / "tone.wav"
    make_wav(path, 3)
    print("wav:", path, path.stat().st_size, "B")

    backend = AudioBackend()
    states: list[str] = []
    errors: list[str] = []
    backend.stateChanged.connect(states.append)
    backend.errorOccurred.connect(errors.append)

    backend.load(str(path))
    backend.play()
    for _ in range(20):
        app.processEvents()
        time.sleep(0.1)
    print("state:", states, "duration:", backend.duration(), "position:", backend.position())
    backend.seek(1500)
    for _ in range(5):
        app.processEvents()
        time.sleep(0.1)
    print("after seek:", backend.position(), "playing:", backend.is_playing())
    backend.pause()
    app.processEvents()
    print("errors:", errors)
    if errors:
        raise SystemExit("音频后端报错")
    if backend.duration() <= 0:
        raise SystemExit("未能读取时长，QtMultimedia 插件可能缺失")
    print("音频后端冒烟通过")


if __name__ == "__main__":
    main()
