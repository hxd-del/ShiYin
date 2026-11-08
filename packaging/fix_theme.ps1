$configPath = "$env:LOCALAPPDATA\ShiYin\config.json"
$config = Get-Content $configPath -Raw | ConvertFrom-Json
$config.theme = 'light'
$config | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
Write-Host "配置已修改：theme = light"
