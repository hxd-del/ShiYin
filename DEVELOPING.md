# 拾音 ShiYin 源码说明（交给接手开发的智能体）

## 1. 这是什么

基于 `musicdl` 二次开发的 **PySide6 桌面音乐播放器**，交付两种形态：

| 产物 | 生成方式 | 说明 |
| --- | --- | --- |
| `ShiYin-Setup-*.exe` | `packaging\installer.spec`（自研单文件安装器） | 内置整包负载，支持 `--silent / --dir / --no-shortcuts / --no-registry / --no-launch` |
| `ShiYin-Portable-*.7z` | `packaging\make_portable.py` + `portable.ps1` | 解压即用，含 `portable.flag`，数据落在程序目录 `data\` |
| `dist\ShiYin\`（onedir） | `packaging\shiyin.spec` | 两个产物都从这里取材 |

技术栈：Python 3.13 + PySide6 6.12（QtMultimedia/ffmpeg 后端）+ SQLite + PyInstaller 6.22。
运行环境：Windows 10/11；构建机 Python 3.13 虚拟环境 `.venv`。

## 2. 目录结构

```
shiyin\                         应用源码（全部自己写的代码都在这里）
├─ __init__.py                  版本号、应用名常量
├─ __main__.py                  python -m shiyin 入口
├─ sources.json                 音源白名单（whitelist / enabled_default / excluded）
├─ app\
│  ├─ main.py                   进程入口：单实例、命令行 --search 自检、退出收敛
│  ├─ bootstrap.py              日志/异常钩子准备
│  ├─ context.py                组装根：配置 → 数据库 → 适配层 → 服务，UI 只依赖它
│  ├─ paths.py                  数据目录解析（便携模式 vs 安装模式）
│  ├─ adapters\
│  │  ├─ musicdl_adapter.py     唯一 import musicdl 的地方：白名单实例化、SongInfo→Track、并发搜索、直链解析
│  │  ├─ progress_bridge.py     把 rich Progress 桥到 Qt 信号
│  │  └─ source_catalog.py      读 sources.json，提供中文源名
│  ├─ core\
│  │  ├─ models.py              Track / DownloadTask / SearchResult、归一化与合并键
│  │  ├─ audio_backend.py       QtMultimedia 播放封装
│  │  ├─ stream_cache.py        本地 HTTP 流缓存（边下边播、Range、TTL）
│  │  └─ single_instance.py     单实例互斥
│  ├─ services\
│  │  ├─ search_service.py      并发编排、跨源归并开关、源健康统计
│  │  ├─ download_service.py    下载队列、断点续传、HLS 交给上游、入库
│  │  ├─ library_service.py     本地目录扫描与指纹去重
│  │  ├─ playback_service.py    播放队列、循环模式、失败换源
│  │  └─ settings_service.py    配置读写、路径自愈、旧默认音源迁移
│  ├─ data\
│  │  ├─ db.py                  SQLite 连接与建表
│  │  └─ repository.py          曲库/歌单/播放历史的读写
│  └─ ui\
│     ├─ mainwindow.py          左侧导航 + 右侧页面 + 底部播放栏
│     ├─ theme.py               深/浅色主题 QSS
│     ├─ models\track_model.py  列表模型（标题/歌手/专辑/时长/音质/来源）
│     ├─ widgets\player_bar.py  播放控件
│     └─ pages\                 search / library / playlists / downloads / settings
├─ vendor\                      裁剪过的 musicdl（**不要手改**，会被 scripts\build_whitelist.py 覆盖）
packaging\                      PyInstaller spec、安装器、便携打包、图标
scripts\                        构建校验、冒烟、探针、对比工具（见第 5 节）
tests\                          test_core.py / test_services.py（16 例）
SHIYIN.md                       工程笔记：设计取舍、打包坑、搜索链路、已知限制
requirements-shiyin.txt         应用侧依赖
requirements.txt                上游 musicdl 的依赖（vendor 需要它）
```

## 3. 运行

```powershell
# 开发期跑源码（必须给可写数据目录，工程根当数据目录会 SQLite disk I/O error）
$env:SHIYIN_DATA_DIR = "D:\work\shiyin-data"
.\.venv\Scripts\python.exe -m shiyin

# 无界面自检：走同一套服务，结果写 JSON，适合在冻结产物上量条数与耗时
.\.venv\Scripts\python.exe -m shiyin --search 晴天 --out D:\work\result.json
```

`--search` 输出的 JSON 含 `total` / `elapsed_ms` / `per_source`（每源条数）/ `errors`（每源失败原因）/ `items`（前 100 条）。
`--sources A,B` 可临时指定音源。

## 4. 打包

```powershell
pwsh packaging\build.ps1                 # 全量：onedir → 自检 → 安装器 → 便携 7z
pwsh packaging\build.ps1 -SkipInstaller  # 只出 onedir + 7z
```

`build.ps1` 会先把工程根的 `musicdl\` 改名成 `musicdl_upstream\` 再构建，否则 PyInstaller 会打进来一份未裁剪的上游。

## 5. 校验工具

| 脚本 | 用途 |
| --- | --- |
| `scripts\build_whitelist.py --check` | 校验 `sources.json` 白名单与 vendor 是否一致 |
| `scripts\launch_check.py <exe> <data>` | 冻结产物启动 + 数据库可写自检 |
| `scripts\portable_check.py` | 检查 7z 条目（`portable.flag`、`fake_useragent\data\browsers.jsonl`、无 data/logs） |
| `scripts\smoke_ui.py` | 五个页面 + 播放栏冒烟 |
| `scripts\smoke_search.py` / `smoke_services.py` / `smoke_audio.py` | 搜索/服务/播放链路冒烟 |
| `scripts\compare_search.py` | 同一次搜索里对比「分源原始条数」与「跨源合并后条数」 |
| `scripts\probe_sources.py` / `probe_dupes.py` | 单源串行探针 / 单源原始条目查重 |
| `python -m unittest discover -s tests` | 16 例单测 |

## 6. 必须知道的坑（改代码前先读）

1. **数据目录**：源码模式不设 `SHIYIN_DATA_DIR` 会 `sqlite3.OperationalError: 无法创建可写的数据库`。
   便携模式数据落在程序目录 `data\`；安装模式落在 `%LOCALAPPDATA%\ShiYin`。
2. **fake_useragent 数据文件**：`shiyin.spec` 里必须有 `collect_data_files("fake_useragent")`，
   否则打包后每个音源初始化都抛 `FakeUserAgentError`，搜索 0.1 秒返回 0 条。
3. **便携打包的 `ignore_patterns`**：`shutil.ignore_patterns("data")` 按 basename 任意深度匹配，会把
   `_internal\fake_useragent\data` 一起删掉；`make_portable.py` 已改成只在顶层忽略。
4. **PyInstaller onefile** 必须 `runtime_tmpdir="."`（便携/受限目录），否则报 `Could not create temporary directory!`。
5. **异常收敛**：上游绝大多数 `requests` 调用不传 timeout，`install_http_timeout()` 给 12 秒兜底；
   搜索线程池手动 `shutdown(wait=False, cancel_futures=True)`，用 `with` 会把已超时的慢源等回来。
6. **不要手改 `shiyin\vendor\`**：白名单脚本会按 `sources.json` 重新生成它。
7. **PowerShell**：用 7.x；`-Encoding utf8` 不带 BOM；读日志中文用 `.venv\Scripts\python.exe` 更稳。

## 7. 当前搜索配置（容易被误改）

| 参数 | 值 | 理由 |
| --- | --- | --- |
| 默认音源 | `sources.json` 里 36 个（原 41，剔除 5 个永远不可用的） | 每个可用源都参与，条数才追得上上游终端 |
| 每源结果数 | 5 | 与上游 `musicdl.py` 的 `search_size_per_source: 5` 一致；调到 10 反而只剩十几条 |
| 搜索总预算 | 20 秒（设置可改，上限 60） | 15 秒时会砍掉 32 个源，20 秒降到 15~17 个 |
| 并发 | 16（`SHIYIN_SEARCH_WORKERS` 可覆盖） | 41 并发会被源站限流，43 条掉到 19 条 |
| 跨源合并 | 默认关闭，搜索页「合并同曲」可开 | 合并后同曲只留音质最高一条，是"看着变少"的主因 |
| 无直链结果 | 保留 | 点播/下载时 `adapter.resolve → refresh` 再解析，搜索阶段不丢 |

实测（构建机网络，"晴天"）：36 源 / 每源 5 条 / 20 秒 → **67 条**，15 个源失败；
修复前（10 源 / 每源 8 条 / 12 秒）只有 24 条。

## 8. 已实现能力 / 未实现

已实现：多源聚合搜索（边搜边上屏、按源筛显示）、直链试听（流缓存 + Range）、下载队列（续传/暂停/重试/入库）、
本地曲库扫描、收藏/最近/自建歌单、播放队列与循环模式、失败自动换源、托盘最小化、音源勾选与「检测音源」。

未实现：歌词面板与歌词服务、封面抓取缓存、下载任务的持久化恢复、搜索结果按源分组筛选面板、
`core\task_queue.py`；`ape/wv` 在 QtMultimedia ffmpeg 后端能否播放尚未实测。

## 9. 接手建议

- 新增功能优先落在 `shiyin\app\services\`（业务）与 `shiyin\app\ui\pages\`（界面），经 `context.py` 注入，别让 UI 直接 new 服务。
- 任何涉及音源的改动都先跑 `scripts\compare_search.py` + `scripts\smoke_search.py`，再看 `--search` 的 `per_source`。
- 改动后按「单测 → smoke_ui → build.ps1 → launch_check/portable_check」顺序验，最后用冻结产物跑一次 `--search` 再交付。
