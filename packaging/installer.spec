# ------------------------------------------------------------------
# 拾音安装器打包配方：单文件 EXE，内置 dist\ShiYin 作为负载
# 用法：pyinstaller packaging\installer.spec --noconfirm
# ------------------------------------------------------------------
import sys
from pathlib import Path
import os

ROOT = Path(SPECPATH).resolve().parent
PAYLOAD = ROOT / "dist" / "ShiYin"
if not PAYLOAD.exists():
    raise SystemExit("先构建 dist\\ShiYin（pyinstaller packaging\\shiyin.spec）")

sys.path.insert(0, str(ROOT))
from shiyin import __version__  # noqa: E402

datas = [(str(PAYLOAD), "payload/ShiYin")]

a = Analysis(
    [str(ROOT / "packaging" / "installer_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "shiyin", "musicdl", "tkinter", "unittest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f"ShiYin-Setup-{__version__}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=bool(os.environ.get("SHIYIN_INSTALLER_CONSOLE")),
    runtime_tmpdir=".",  # 解包到安装器同目录：%TEMP% 在受限环境里可能不可写
    icon=str(ROOT / "packaging" / "shiyin.ico"),
)
