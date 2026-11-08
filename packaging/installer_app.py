"""拾音安装器：单文件 EXE，内置 app 负载，负责安装/卸载与快捷方式。

用法：
    ShiYin-Setup.exe                 图形安装（默认装到 %LOCALAPPDATA%\\Programs\\ShiYin）
    ShiYin-Setup.exe --silent        静默安装
    ShiYin-Setup.exe --silent --dir D:\\Apps\\ShiYin
    ShiYin-Setup.exe --uninstall --silent
"""

from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import winreg
from pathlib import Path

APP_NAME = "ShiYin"
APP_DISPLAY = "拾音"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\ShiYin"


def payload_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "payload" / "ShiYin"


def default_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Programs" / APP_NAME


def message(text: str, title: str = APP_DISPLAY, error: bool = False) -> None:
    flags = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(None, text, title, flags)


def make_shortcut(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{link}');"
        "$s.TargetPath='{target}';$s.WorkingDirectory='{work}';$s.IconLocation='{target},0';$s.Save()"
    ).format(link=link, target=target, work=target.parent)
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                   capture_output=True, creationflags=0x08000000)


def write_registry(target: Path, uninstaller: Path) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_DISPLAY)
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(target / "ShiYin.exe"))
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "0.1.0")
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "ShiYin")
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(target))
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller}" --uninstall')


def install(target: Path, shortcuts: bool, registry: bool) -> None:
    source = payload_dir()
    if not source.exists():
        raise RuntimeError(f"安装包缺少负载目录: {source}")
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)

    # 复制安装器自身，供"卸载"和"修复安装"使用
    uninstaller = target / "ShiYin-Setup.exe"
    if not uninstaller.exists() and getattr(sys, "frozen", False):
        shutil.copy2(sys.executable, uninstaller)

    if shortcuts:
        make_shortcut(Path(os.environ["USERPROFILE"]) / "Desktop" / f"{APP_DISPLAY}.lnk",
                      target / "ShiYin.exe")
        make_shortcut(Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu"
                      / "Programs" / f"{APP_DISPLAY}.lnk", target / "ShiYin.exe")
    if registry:
        write_registry(target, uninstaller)


def uninstall(target: Path, shortcuts: bool, registry: bool) -> None:
    if shortcuts:
        for link in (Path(os.environ["USERPROFILE"]) / "Desktop" / f"{APP_DISPLAY}.lnk",
                     Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu"
                     / "Programs" / f"{APP_DISPLAY}.lnk"):
            try:
                link.unlink()
            except OSError:
                pass
    if registry:
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        except OSError:
            pass
    # 数据目录（数据库、下载）不在程序目录里，默认保留；--purge 才删
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--dir")
    parser.add_argument("--silent", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--no-shortcuts", action="store_true")
    parser.add_argument("--no-registry", action="store_true")
    parser.add_argument("--no-launch", action="store_true")
    parser.add_argument("--purge", action="store_true", help="卸载时同时删除用户数据目录")
    args, _ = parser.parse_known_args()

    target = Path(args.dir) if args.dir else default_dir()
    try:
        if args.uninstall:
            uninstall(target, not args.no_shortcuts, not args.no_registry)
            if args.purge:
                shutil.rmtree(Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ShiYin",
                              ignore_errors=True)
            if not args.silent:
                message("拾音已卸载。")
            return 0

        install(target, not args.no_shortcuts, not args.no_registry)
    except Exception as err:  # noqa: BLE001
        if not args.silent:
            message(f"安装失败：{err}", error=True)
        print(f"install failed: {err}", file=sys.stderr)
        return 1

    if not args.silent:
        message(f"拾音已安装到：\n{target}\n\n安装完成后可直接从桌面或开始菜单启动。")
    if not args.no_launch and not args.silent:
        subprocess.Popen([str(target / "ShiYin.exe")], cwd=str(target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
