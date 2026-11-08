$configPath = "$env:LOCALAPPDATA\ShiYin\config.json"
$config = Get-Content $configPath -Raw | ConvertFrom-Json
$config.download_dir = "C:\Users\HP\AppData\Local\ShiYin\library"
$config.library_dir = "C:\Users\HP\AppData\Local\ShiYin\library"
$config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
Write-Host "下载目录已修复：C:\Users\HP\AppData\Local\ShiYin\library"
