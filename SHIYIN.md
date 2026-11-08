# 拾音 ShiYin

基于 [musicdl](https://github.com/CharlesPikachu/musicdl) 2.14.2 二次开发的桌面音乐播放器：多源聚合搜索、单曲试听、下载队列、本地库、歌单，PySide6 界面，可打包成安装版与便携版。

上游代码只保留白名单内的 41 个音源（去掉 DRM、`.wvd` 与 Apple/TIDAL/SoundCloud 工具模块），裁剪结果落在 `shiyin/vendor/musicdl`，由 `scripts/build_whitelist.py` 生成，**不要手工改 vendor 目录**。

## 目录

```
shiyin/
  sources.json          音源白名单（裁剪脚本与界面共用的唯一真源）
  __init__.py           版本号真源 + vendor 路径注入
  app/
    paths.py            安装版写 %LOCALAPPDATA%，便携版写程序目录 data/
    bootstrap.py        日志、stdout 守卫、崩溃转储
    context.py          组装根：配置 → 数据库 → 适配层 → 服务层 → 播放
    core/               models / stream_cache / audio_backend / single_instance
    data/               db.py（建表+journal 探针）/ repository.py（全部 SQL）
    adapters/           musicdl_adapter.py（唯一 import musicdl 的地方）/ source_catalog / progress_bridge
    services/           settings / search / download / library / playback
    ui/                 mainwindow / theme / pages(5) / widgets(player_bar) / models(track_model)
scripts/                build_whitelist.py、smoke_*.py
packaging/              shiyin.spec、installer.iss、portable.ps1、build.ps1、make_icon.py
tests/                  test_core.py、test_services.py
```

## 开发运行

```powershell
.\.venv\Scripts\python.exe -m shiyin
```

## 测试

```powershell
# 单元测试（16 项，内存库，不联网）
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# 服务层链路：本地假源 → 流缓存 → Range → 下载 → 入库
.\.venv\Scripts\python.exe scripts\smoke_services.py

# 界面：离屏创建主窗口与全部页面
.\.venv\Scripts\python.exe scripts\smoke_ui.py

# 音频后端：生成 3 秒 wav，验证加载/播放/拖动
.\.venv\Scripts\python.exe scripts\smoke_audio.py

# 真实音源联调（需联网）
.\.venv\Scripts\python.exe scripts\smoke_search.py 晴天
```

## 打包

```powershell
pwsh packaging\build.ps1            # 白名单校验 → PyInstaller onedir → 自检 → 安装程序 → 便携 7z
pwsh packaging\build.ps1 -SkipInstaller -SkipPortable   # 只出 onedir
```

- onedir 产物：`dist\ShiYin\`（约 193 MB，`ShiYin.exe` 12.8 MB）
- 安装程序：`dist\ShiYin-Setup-<version>.exe`（单文件，内置整包负载；装了 Inno Setup 6 且存在
  `ISCC.exe` 时改走 `packaging\installer.iss`，输出到 `dist\installer\`）
- 便携包：`dist\ShiYin-Portable-<version>.7z`（有 7-Zip 用 7-Zip，否则退回 `packaging\make_portable.py` 的 py7zr，LZMA2 preset 9）

安装程序参数：`--silent` 静默、`--dir <路径>` 指定安装目录（默认 `%LOCALAPPDATA%\Programs\ShiYin`）、
`--no-shortcuts` 不建快捷方式、`--no-registry` 不写卸载项、`--uninstall` 卸载（配 `--purge` 一并删用户数据）。

打包四处硬坑（已固化进脚本，别绕开）：

1. 工程根下有一份未裁剪的上游 `musicdl\`（30 个源），`collect_submodules("musicdl")` 会先命中它：
   未打补丁的 logger 启动即写 `%LOCALAPPDATA%\zcjin\musicdl`，在受限环境直接 `WinError 5`。
   `build.ps1` 在构建期间把 `musicdl\` 改名藏起来、构建完在 `finally` 里恢复，`shiyin.spec` 里
   `pathex=[VENDOR, ROOT]` 再兜一层。
2. PyInstaller 的 `--noconfirm` 仍会 `rmtree` 旧目录，Windows 上常被锁成 `WinError 145`；
   统一先 `Rename-Item` 改名再建新目录。onefile 在受限环境还会 `Could not create temporary directory`，
   所以主程序固定 onedir，安装器 onefile 加 `runtime_tmpdir="."`。
3. `fake_useragent` 在 import 时读自带的 `data/browsers.jsonl`，默认不会进包；漏了它每个音源都会在
   初始化阶段抛 `FakeUserAgentError`，现象是**搜索永远 0 条、0.1 秒返回**。`shiyin.spec` 用
   `collect_data_files("fake_useragent")` 显式带上。
4. 便携包要剔除运行时 `data`/`logs`，但 `shutil.ignore_patterns("data")` 按目录名匹配，会连
   `_internal\fake_useragent\data` 一起删掉，同样导致全源不可用。`make_portable.py` 改成只忽略
   **顶层** `data`/`logs`（自定义 `ignore(directory, names)`），`portable.ps1` 也只删顶层路径。

便携模式：解压后目录里存在 `portable.flag`，数据（数据库、配置、缓存、下载）全部写在该目录 `data\` 下，不碰用户目录。


## 数据位置

| 形态 | 数据目录 |
| --- | --- |
| 安装版 | `%LOCALAPPDATA%\ShiYin`（不可写时退化为程序目录 `data`） |
| 便携版 | `<程序目录>\data` |
| 调试 | 设置 `SHIYIN_DATA_DIR` 强制指定 |

## 功能现状

| 模块 | 已实现 |
| --- | --- |
| 搜索 | 默认 41 个音源并发（16 线程）、20 秒预算、边搜边上屏、分源列出 + 可选合并同曲、失败源写 `source_health` |
| 试听 | 本地 HTTP 流缓存代理，边下边播，支持 Range/拖动，直链 403 自动重解析一次 |
| 下载 | 队列 + 并发上限、断点续传、暂停/继续/取消/重试、HLS 交给上游、校验、写标签、入库、试听缓存转正 |
| 本地库 | 目录扫描（大小+首尾哈希指纹去重）、增量跳过、双击播放 |
| 播放列表 | 当前队列查看、双击切歌、移除单首、清空，右键加入歌单 |
| 歌单 | 收藏（右键收藏/取消收藏）、最近播放（最新在前）、自建歌单（新建/重命名/删除、加歌与移除） |
| 播放 | 队列、顺序/列表循环/单曲循环、失败自动换备选源、音量记忆（拖动防抖落盘）、托盘最小化 |
| 交互 | 音量与进度条支持点击直接跳转（不必先瞄准手柄），进度条在时长未知时禁用 |
| 设置 | 目录、并发、每源结果数、缓存上限、超时、代理、主题、音源勾选 |

## 搜索链路

- 源集合取自 `settings.enabled_sources`（未设置时用 `sources.json` 的 `enabled_default`，默认 **全部 41 个源**）。
  旧版本曾把 10 个大陆源写进 config，`SettingsService._migrate_sources()` 会识别这串旧默认并清空，
  回落到全源，否则老用户升级后仍然只搜 10 个源、结果必然偏少。
- 每源结果数默认 5（与上游 `musicdl.py` 的 `search_size_per_source: 5` 一致）。这个值不是越大越好：
  单源请求越多越慢，能赶在预算内落地的源越少，总条数反而下降（实测每源 10 条时只剩 14 条）。
- 单次搜索总预算 `min(设置值, 60) 秒`，默认 20 秒。上游终端不设超时、慢源最终都会返回；
  20 秒 + 流式上屏是"结果数量"和"等待体感"的折中（15 秒时 32 个源被砍，20 秒时降到 17 个）。
- 并发默认 16（`SHIYIN_SEARCH_WORKERS` 可覆盖）。实测 41 并发反而更差（源站限流，43 条 → 19 条），
  不是越高越好。
- **默认不做跨源合并**：同一首歌在各源各占一行，条数与上游终端观感一致，用户自己挑来源；
  搜索页「合并同曲」打开后才按 `(歌名, 主歌手, 时长±3s)` 归并，只留音质最高的一条，其余进 `Track.alternatives`。
  同源内仍去重，但键里带 `ext/size/bitrate`，同名不同格式（FLAC/MP3）都会保留。
- 搜索阶段不再丢弃"没有直链"的结果：这类条目在点播/下载时由 `adapter.resolve → refresh` 按同源重搜解析。
- 超时后 `pool.shutdown(wait=False, cancel_futures=True)`，不会把已判超时的慢源继续等回来。
- `install_http_timeout()` 给上游所有 `requests` 调用兜底 12 秒，避免单源把线程挂到分钟级。
- 无界面自检：`ShiYin.exe --search 晴天 --out result.json`，输出 `total` / `per_source` / `errors`（items 取前 100 条）。
- 设置页「检测音源」并发试搜一遍，逐源显示条数/超时，建议只保留可用源后保存。

实测（构建机网络，2026-11-06，关键词"晴天"）：41 源、每源 5 条、20 秒 → **62 条 / 13 个源有结果**，
对比修复前（10 源、每源 8 条、12 秒）的 24 条。单源探针显示 Kuwo / QQ / Kugou / Netease 等时好时坏，
属上游接口与本地网络双重影响，换网络或配代理可改善。

## 已知限制

- **解码范围**：QtMultimedia 6.12 的 ffmpeg 后端可解 mp3/flac/m4a/wav/ogg；ape/wv 是否可播取决于 ffmpeg 解码器，需实机抽查。
- **HLS 音源**：上游 `HLSDownloader` 依赖 ffmpeg / N_m3u8DL-RE，本程序不内置（体积约 80–120 MB），启动时按需提示。
- **QQ 源**：实测匿名搜索可能返回空，属上游接口限流，界面会显示该源失败原因。
- **SQLite**：`db.connect` 会探测 WAL 是否真的可写，失败自动退到 `journal_mode=MEMORY`（部分网络盘/受限文件系统上 WAL 会静默失败）。
- **歌词/封面**：数据表已留字段，界面尚未接（P2）。
- **单实例**：用 `QLocalServer` 命名管道实现，多用户同一台机器共用一个名字，暂未按用户隔离。

## 版本

`shiyin/__init__.py::__version__` 是唯一真源，打包脚本从中读取并传给 Inno Setup。
