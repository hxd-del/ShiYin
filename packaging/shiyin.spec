# ------------------------------------------------------------------
# 拾音 ShiYin 打包配方：PyInstaller onedir + 无控制台
# 用法：pyinstaller packaging/shiyin.spec --clean --noconfirm
# ------------------------------------------------------------------
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parent          # 项目根目录（含 shiyin/）
VENDOR = ROOT / "shiyin" / "vendor"
sys.path.insert(0, str(VENDOR))                 # 让 collect_submodules 能扫描到裁剪后的 musicdl

datas = [
    (str(ROOT / "shiyin" / "sources.json"), "shiyin"),
]
# fake_useragent 在 import 时会读自带的 browsers.json；漏掉它，每个音源都会
# 在初始化阶段抛 FakeUserAgentError，表现为「打包版搜索一条结果都没有」。
datas += collect_data_files("fake_useragent")

hiddenimports = collect_submodules("musicdl")
# 封面从本地音频抽取：mutagen.File 会按格式动态载入 mp3/flac/mp4 等子模块，
# 静态分析只看到顶层的 import mutagen，打包版会漏掉这些格式插件。
hiddenimports += collect_submodules("mutagen")
hiddenimports += [
    "shiyin.app.main",
    "shiyin.app.context",
    "shiyin.app.ui.mainwindow",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtMultimedia",
    "PySide6.QtNetwork",
]

excludes = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.Qt3DCore", "PySide6.QtBluetooth", "PySide6.QtPositioning", "PySide6.QtSerialPort",
    "tkinter", "test", "unittest", "pydoc_data",
]

a = Analysis(
    [str(ROOT / "shiyin" / "__main__.py")],
    # VENDOR 必须排在 ROOT 之前：ROOT 下还有一份未裁剪的上游 musicdl，
    # 顺序反了会把 30 个源（含 DRM 模块）打进包里。
    pathex=[str(VENDOR), str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ShiYin",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "packaging" / "shiyin.ico") if (ROOT / "packaging" / "shiyin.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ShiYin",
)
