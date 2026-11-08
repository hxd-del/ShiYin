@echo off
chcp 65001 >nul
title 清理旧版拾音安装痕迹

echo ========================================
echo    清理旧版拾音 (ShiYin) 安装痕迹
echo ========================================
echo.

:: 停止可能运行的进程
echo [1/5] 停止 ShiYin 进程...
taskkill /F /IM ShiYin.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq *拾音*" 2>nul
timeout /t 2 /nobreak >nul

:: 删除安装目录
echo [2/5] 删除安装目录...
if exist "C:\Users\%USERNAME%\AppData\Local\Programs\ShiYin" (
    rmdir /s /q "C:\Users\%USERNAME%\AppData\Local\Programs\ShiYin"
    echo   已删除 C:\Users\%USERNAME%\AppData\Local\Programs\ShiYin
) else (
    echo   目录不存在，跳过
)

:: 删除开始菜单快捷方式
echo [3/5] 删除开始菜单快捷方式...
if exist "C:\Users\%USERNAME%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\拾音.lnk" (
    del /f "C:\Users\%USERNAME%\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\拾音.lnk"
    echo   已删除开始菜单快捷方式
) else (
    echo   快捷方式不存在，跳过
)

:: 删除注册表卸载信息
echo [4/5] 删除注册表卸载信息...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\拾音" /f 2>nul
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\ShiYin" /f 2>nul
echo   注册表已清理

:: 刷新系统
echo [5/5] 刷新系统...
ie4uinit.exe -show 2>nul
taskkill /F /IM explorer.exe 2>nul
timeout /t 2 /nobreak >nul
start explorer.exe

echo.
echo ========================================
echo  清理完成！
echo ========================================
echo.
echo 注意：以下数据已保留（便携版和源码版共用）：
echo   - C:\Users\%USERNAME%\AppData\Local\ShiYin\
echo     (包含配置、缓存、下载记录等)
echo.
pause
