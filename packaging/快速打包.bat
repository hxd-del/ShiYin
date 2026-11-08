@echo off
chcp 65001 >nul
title 快速打包 ShiYin

echo ========================================
echo    快速打包 ShiYin (含托盘修复)
echo ========================================
echo.

cd /d "%~dp0\.."

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
echo [1/2] 安装依赖...
%PYTHON% -m pip install pyinstaller py7zr -q

echo.
echo [2/2] 开始打包...
%PYTHON% -m PyInstaller packaging\shiyin.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo  打包完成!
echo  输出: dist\ShiYin\ShiYin.exe
echo ========================================
echo.
echo 是否复制新文件到 ShiYin-0.1.0 目录?
echo.
set /p copy="请输入 Y 确认，其他键跳过: "

if /i "%copy%"=="Y" (
    if exist "dist\ShiYin\ShiYin.exe" (
        copy /Y "dist\ShiYin\ShiYin.exe" "..\ShiYin-Portable-0.1.0\ShiYin-0.1.0\ShiYin.exe"
        echo 已复制到 ShiYin-0.1.0 目录
    )
    if exist "dist\ShiYin\_internal" (
        xcopy /E /Y /Q "dist\ShiYin\_internal" "..\ShiYin-Portable-0.1.0\ShiYin-0.1.0\_internal\" >nul
        echo 已更新 _internal 目录
    )
)

echo.
pause
