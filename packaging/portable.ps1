# 生成便携版：复制 onedir 产物 + 打 portable.flag + 压缩成 7z
# 优先用 7-Zip（LZMA2 -mx=9），没装就退回 py7zr。
# 用法：pwsh packaging\portable.ps1 -Version 0.1.0

param(
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$SevenZip = ""
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$src = Join-Path $root "dist\ShiYin"
if (-not (Test-Path -LiteralPath $src)) {
    throw "找不到 dist\ShiYin，请先运行 pyinstaller packaging\shiyin.spec --noconfirm"
}

if (-not $SevenZip) {
    $candidates = @(
        "C:\Program Files\7-Zip\7z.exe",
        "C:\Program Files (x86)\7-Zip\7z.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) { $SevenZip = $candidate; break }
    }
}

if (-not $SevenZip) {
    Write-Host "未找到 7z.exe，改用 py7zr 生成 7z"
    & (Join-Path $root ".venv\Scripts\python.exe") (Join-Path $root "packaging\make_portable.py") $Version
    exit $LASTEXITCODE
}

$staging = Join-Path $root "dist\portable\ShiYin-$Version"
if (Test-Path -LiteralPath $staging) {
    $staging = "$staging-$(Get-Date -Format 'HHmmss')"
}
New-Item -ItemType Directory -Path $staging -Force | Out-Null
Copy-Item -Path (Join-Path $src "*") -Destination $staging -Recurse -Force
# data / 日志是运行时产物，绝不能进便携包：里面的 config 还带着构建机的绝对路径
foreach ($runtimeDir in @("data", "logs", "_internal\logs")) {
    $victim = Join-Path $staging $runtimeDir
    if (Test-Path -LiteralPath $victim) {
        Remove-Item -LiteralPath $victim -Recurse -Force -ErrorAction SilentlyContinue
    }
}
Set-Content -LiteralPath (Join-Path $staging "portable.flag") -Value "ShiYin portable" -Encoding ascii

$archive = Join-Path $root "dist\ShiYin-Portable-$Version.7z"
& $SevenZip a $archive $staging -t7z -m0=lzma2 -mx=9 -md=64m -mmt=on | Out-Null
$sizeMb = [math]::Round((Get-Item -LiteralPath $archive).Length / 1MB, 1)
Write-Host "便携包: $archive ($sizeMb MB)"
