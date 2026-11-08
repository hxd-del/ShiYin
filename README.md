# 拾音 ShiYin

基于 [musicdl](https://github.com/CharlesPikachu/musicdl) 2.14.2 二次开发的 Windows 桌面音乐播放器：多源聚合搜索、单曲试听、下载队列、本地库、歌单、收藏与最近播放，PySide6 界面，可打包为安装版或便携版。

## 功能

- 多源聚合搜索与单曲试听
- 下载队列、本地库扫描与入库
- 收藏、最近播放、自建歌单、播放队列
- 播放位置 / 队列 / 当前曲目 / 上次页面 / 窗口尺寸记忆
- 启动时按设置目录扫描本地库
- 浅色 / 深色主题，可打包为 onedir、安装程序或便携包

## 环境要求

- Windows 10/11
- Python 3.12（项目开发使用 3.12）
- PySide6 6.12（`PySide6-Essentials` + `PySide6-Addons`）

## 快速开始

```powershell
git clone https://github.com/hxd-del/ShiYin.git
cd ShiYin

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-shiyin.txt
python -m shiyin
```

## 数据目录

- 安装版 / 普通运行：`%LOCALAPPDATA%\ShiYin`
- 便携版：在程序目录放 `portable.flag`，数据写到程序目录下的 `data\`
- 可用环境变量 `SHIYIN_DATA_DIR` 指定独立数据目录（测试时常用）

数据库、日志、下载的音频、封面/歌词、用户配置都属于运行时数据，已在 `.gitignore` 中排除，不要提交到仓库。

## 目录结构

```text
shiyin/
  sources.json          音源白名单
  app/
    paths.py            数据目录判定
    bootstrap.py        日志、崩溃转储
    context.py          配置 / 数据库 / 适配层 / 服务组装
    core/               模型、缓存、音频后端、单实例
    data/               SQLite 建表、Repository
    adapters/           musicdl 适配层
    services/           搜索、下载、本地库、播放、设置、会话记忆
    ui/                 主窗口、主题、页面、播放条
  vendor/musicdl/       按白名单裁剪的上游 musicdl（不要手工修改）
scripts/                白名单生成、烟测脚本
packaging/              PyInstaller / Inno Setup / 便携包脚本
tests/                  单元测试
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_core.py"
.\.venv\Scripts\python.exe scripts\smoke_ui.py
.\.venv\Scripts\python.exe scripts\smoke_audio.py
```

需要联网的搜索联调：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_search.py 晴天
```

## 打包

```powershell
pwsh packaging\build.ps1
```

常用参数：

```powershell
pwsh packaging\build.ps1 -SkipInstaller -SkipPortable   # 只出 dist\ShiYin\
```

`dist\`、`build\`、`.venv\` 都是构建产物，不提交到 Git；安装包、便携包和发布用的压缩包请放到 GitHub Releases。

## 许可

- 本仓库包含的上游 `musicdl` 采用 **PolyForm Noncommercial License 1.0.0**，仅限非商业用途。
- 上游许可证全文：`third_party/musicdl/LICENSE`
- 修改与分发说明：`THIRD_PARTY_NOTICES.md`
- 本仓库自有代码的许可证尚未指定；公开前请根据发布意图补充根目录 `LICENSE`。
