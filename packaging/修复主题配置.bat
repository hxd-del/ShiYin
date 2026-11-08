@echo off
chcp 65001 >nul
echo 修复 ShiYin 主题配置...
echo.

:: 修改 AppData 中的配置文件
set CONFIG_FILE=%LOCALAPPDATA%\ShiYin\config.json

if exist "%CONFIG_FILE%" (
    echo 找到配置文件：%CONFIG_FILE%
    echo 正在修改主题为浅色...
    
    :: 使用 PowerShell 修改 JSON
    powershell -Command "$config = Get-Content '%CONFIG_FILE%' -Raw | ConvertFrom-Json; $config.theme = 'light'; $config | ConvertTo-Json -Depth 10 | Set-Content '%CONFIG_FILE%' -Encoding UTF8"
    
    echo 修改完成！
    echo.
    echo 请重启 ShiYin 应用以生效。
) else (
    echo 未找到配置文件：%CONFIG_FILE%
)

echo.
pause
