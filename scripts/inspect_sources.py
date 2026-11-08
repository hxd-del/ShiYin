"""看一眼白名单里有哪些源在初始化阶段就注定失败（需要额外配置）。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / "shiyin" / "sources.json").read_text(encoding="utf-8"))
names = [n for group in data["whitelist"].values() for n in group]
print("whitelist:", len(names))
suspects = ["XiagebaMusicClient", "FiveSongMusicClient", "KKWSMusicClient",
            "HeishanMusicClient", "MP3JuiceMusicClient"]
for name in suspects:
    print(name, "in whitelist:", name in names, "| in excluded:", name in data.get("excluded", []))
print("enabled_default:", len(data.get("enabled_default", [])))
