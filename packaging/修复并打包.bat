@echo off
chcp 65001 >nul
title 修复并打包 ShiYin

echo ========================================
echo    修复并打包 ShiYin (含 PySide6 DLL 修复)
echo ========================================
echo.

cd /d "%~dp0"

:: 尝试使用虚拟环境
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo 使用虚拟环境 Python
) else (
    :: 尝试使用系统 Python
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 Python，请安装 Python 3.8+ 或创建虚拟环境
        pause
        exit /b 1
    )
    set PYTHON=python
    echo 使用系统 Python
)

echo.
echo [1/4] 安装/更新依赖...
%PYTHON% -m pip install PySide6 pyinstaller py7zr -q --upgrade
if errorlevel 1 (
    echo [警告] 部分依赖安装失败，尝试继续...
)

echo.
echo [2/4] 检查 PySide6 安装...
%PYTHON% -c "from PySide6.QtCore import QT_VERSION_STR; print('PySide6 版本:', QT_VERSION_STR)"
if errorlevel 1 (
    echo [错误] PySide6 安装失败
    pause
    exit /b 1
)

echo.
echo [3/4] 开始打包...
%PYTHON% -m PyInstaller packaging\shiyin.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    echo.
    echo 请检查：
    echo 1. 是否安装了 PySide6: pip install PySide6
    echo 2. 是否有足够的磁盘空间
    pause
    exit /b 1
)

echo.
echo [4/4] 打包完成!
echo.
echo ========================================
echo  输出文件: dist\ShiYin\ShiYin.exe
echo ========================================
echo.
echo 是否复制新文件到 ShiYin-0.1.0 目录?
echo.
set /p copy="请输入 Y 确认，其他键跳过: "

if /i "%copy%"=="Y" (
    if exist "dist\ShiYin\ShiYin.exe" (
        copy /Y "dist\ShiYin\ShiYin.exe" "..\ShiYin-Portable-0.1.0\ShiYin-0.1.0\ShiYin.exe"
        echo 已复制 ShiYin.exe
    )
    if exist "dist\ShiYin\_internal" (
        echo 正在更新 _internal 目录...
        xcopy /E /Y /Q "dist\ShiYin\_internal" "..\ShiYin-Portable-0.1.0\ShiYin-0.1.0\_internal\" >nul
        echo 已更新 _internal 目录
    )
    echo.
    echo 完成！现在可以运行新的 ShiYin.exe 了
)

echo.
pause
