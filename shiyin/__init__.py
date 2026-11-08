"""拾音音乐播放器。

版本号唯一真源：构建脚本与安装包版本都从这里读取。
"""

from __future__ import annotations

import os
import sys

__version__ = "0.1.0"
APP_NAME = "ShiYin"
APP_DISPLAY_NAME = "拾音"

# 优先使用裁剪后的 vendor 副本（无 DRM 模块、无 .wvd），保证开发与打包行为一致
_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(os.path.join(_VENDOR_DIR, "musicdl")) and _VENDOR_DIR not in sys.path:
    sys.path.insert(0, _VENDOR_DIR)
