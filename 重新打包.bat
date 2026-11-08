@echo off
chcp 65001 >nul
title 重新打包 ShiYin

echo ========================================
echo    重新打包 ShiYin (含托盘修复)
echo ========================================
echo.

cd /d "%~dp0"

:: 检查 Python 虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到 Python 虚拟环境
    echo.
    echo 请先创建虚拟环境：
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo   pip install pyinstaller
    pause
    exit /b 1
)

set PYTHON=.venv\Scripts\python.exe

echo [1/3] 检查音源白名单...
%PYTHON% scripts\build_whitelist.py --check
if errorlevel 1 (
    echo [警告] 白名单检查失败，继续打包...
)

echo.
echo [2/3] 使用 PyInstaller 打包...
%PYTHON% -m PyInstaller packaging\shiyin.spec --noconfirm
if errorlevel 1 (
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)

echo.
echo [3/3] 打包完成!
echo.
echo ========================================
echo  输出文件: dist\ShiYin\ShiYin.exe
echo ========================================
echo.
echo 你可以将新的 ShiYin.exe 复制到 ShiYin-0.1.0 目录替换原文件
echo.
pause
