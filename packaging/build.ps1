# 一键构建：白名单检查 → PyInstaller onedir → 安装包 → 便携 7z
# 用法：pwsh packaging\build.ps1 [-SkipInstaller] [-SkipPortable]

param(
    [switch]$SkipInstaller,
    [switch]$SkipPortable
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $root ".venv\Scripts\python.exe"
Set-Location $root

$version = (& $python -c "import shiyin; print(shiyin.__version__)").Trim()
Write-Host "版本: $version"

Write-Host "[1/4] 校验音源白名单"
& $python scripts\build_whitelist.py --check

Write-Host "[2/4] PyInstaller onedir"
# 两条坑：1) 工程根下还有一份未裁剪的上游 musicdl，模块搜索顺序错会把 30 个源打进来，
# 所以构建期间先把它改名藏起来；2) 杀毒/索引器常锁住 dist 文件，直接删会报"目录不是空的"，
# 改成先改名再建新目录。
$upstream = Join-Path $root "musicdl"
$hold = Join-Path $root "musicdl_upstream"
$movedUpstream = $false
if (Test-Path -LiteralPath $upstream) {
    Rename-Item -LiteralPath $upstream -NewName "musicdl_upstream"
    $movedUpstream = $true
    Write-Host "  构建期间隐藏上游目录 musicdl/"
}
try {
    foreach ($dir in @("build\shiyin", "dist\ShiYin")) {
        if (Test-Path -LiteralPath $dir) {
            $leaf = (Split-Path -Leaf $dir) + "_prev_" + (Get-Date -Format "HHmmss")
            try {
                Rename-Item -LiteralPath $dir -NewName $leaf -ErrorAction Stop
                Write-Host "  旧产物已改名: $leaf"
            } catch {
                Write-Warning "无法移动 $dir：$($_.Exception.Message)"
            }
        }
    }
    & $python -m PyInstaller packaging\shiyin.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller 构建失败" }
} finally {
    if ($movedUpstream -and (Test-Path -LiteralPath $hold) -and -not (Test-Path -LiteralPath $upstream)) {
        Rename-Item -LiteralPath $hold -NewName "musicdl"
        Write-Host "  已恢复上游目录 musicdl/"
    }
}

Write-Host "[3/4] 自检打包产物"
$env:SHIYIN_DATA_DIR = Join-Path $root "build\selftest-data"
& $python scripts\launch_check.py "dist\ShiYin\ShiYin.exe" "build\selftest-data"
if ($LASTEXITCODE -ne 0) { throw "打包产物自检失败，见上面的输出" }

if (-not $SkipInstaller) {
    $iscc = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($iscc) {
        Write-Host "[4/4] Inno Setup 安装包"
        & $iscc "packaging\installer.iss" "/DAppVersion=$version"
        Write-Host "安装包输出在 dist\installer"
    } else {
        Write-Host "[4/4] 内置安装器（未检测到 Inno Setup，用 PyInstaller 打单文件安装程序）"
        & $python -m PyInstaller packaging\installer.spec --noconfirm
        if ($LASTEXITCODE -ne 0) { throw "安装器构建失败" }
        Write-Host "安装包: dist\ShiYin-Setup-$version.exe"
    }
}

if (-not $SkipPortable) {
    Write-Host "生成便携 7z"
    & pwsh -NoProfile -File (Join-Path $root "packaging\portable.ps1") -Version $version
}

Write-Host "完成"
