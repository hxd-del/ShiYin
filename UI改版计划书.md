# 拾音 ShiYin UI 改版计划书

> 参照 QQ 音乐桌面端主界面（1520×932 截图）重排布局。
> 硬约束：**只改摆放与样式，不改任何已有功能行为**。
> 备份：`D:\Users\HP\Desktop\musicdl-master\backup\ShiYin-0.1.0_20261107-181717`
> 创建：2026-11-07　最后更新：2026-11-07

## 1. 目标与边界

目标是把现有界面从"能用的工具"拉到"像播放器"：

- 左侧：分组图标导航 + 快捷入口，替代 7 行纯文字列表。
- 列表：去掉表格边框/表头/斑马纹，行高 64，行首 40px 圆角封面色块。
- 底部：三段式白底播放条（左信息、中控制+进度、右队列/音量/歌词），去掉整条绿色缓冲填充。
- 顶栏：64px，圆角搜索框、细箭头、刷新。
- 配色：QQ 绿 `#2ecb71` 替换现有青绿 `#0f9d90`。

不改的东西（写死在计划里，避免改着改着越界）：

- 不登录、不会员、不做推荐卡片/歌单广场/音质切换/倍速——数据源不支持。
- 导航仍是「我的音乐 / 资源」两组共 6 项 + 底部设置，另有不在导航栏的搜索页；页面内所有按钮、右键菜单、快捷键、托盘行为保持。
- 不改数据库结构、不改 service 对外接口、不改队列/收藏/下载/搜索行为；在线试听在 P4 保持「完整缓存后再播放」的稳定路径，另补可见缓冲反馈（中途试过 `.part` 边下边播，因截断/重试问题已回退）。
- 第五批（P5）只增加“启动记忆 + 启动扫描”这类初始化行为：复用现有 `meta` 表、不新增表；默认恢复后暂停、不自动续播；收藏/最近播放的现有写入语义不变。

## 2. 现状基线（2026-11-07 实测）

| 项 | 现值 |
|---|---|
| 窗口 | `resize(1180, 760)`，最小 960×640，系统标题栏 |
| 左栏 | `QListWidget` 200px，7 行纯文字，整行选中 `#e6f7f5` |
| 顶栏 | 56px，后退/前进 + 搜索框（max 420） |
| 内容页 | 6 个 `QTableView`：带边框、斑马纹、显示表头、行高默认；页头 `sectionTitle` 15px |
| 播放条 | 88px，`paintEvent` 按缓冲进度从左往右铺半透明绿；封面 56；标题/歌手在左；三个文字按钮居中；进度条一行；音量 110px 单独一列 |
| 主色 | `#0f9d90`；背景 `#f7f8fa`；表格选中整行青绿白字 |

## 3. 目标视觉规范

| 用途 | 值 |
|---|---|
| 主色 / hover / pressed | `#2ecb71` / `#28b565` / `#23a55a` |
| 选中浅绿 | `#eafaf0` |
| 页面背景 / 侧栏 / 卡片 | `#f7f8fa` / `#f7f7f7` / `#ffffff` |
| 正文 / 次要 / 分割线 | `#1f2937` / `#8a8f99` / `#eceff3` |
| 字号阶梯 | 页标题 20–22 / 歌名 15 / 正文 13 / 次要 12 |
| 圆角 | 卡片 12，封面 10，按钮 8，搜索框 18（胶囊） |
| 关键尺寸 | 侧栏 232，顶栏 64，播放条 88，列表行 64，封面 40（行内）/56（播放条） |

## 4. 目标布局

```
┌──────────────┬────────────────────────────────────────────────────────┐
│ ◉ 拾音        │  ‹  ›  ↻   [ 🔍 搜索音乐………………… ]                    │ 64
│ ┌────┐┌────┐ │                                                        │
│ │收藏││队列│ │  我的收藏                                              │
│ └────┘└────┘ │  共 N 首                                               │
│ ┌ ─ ─ ─ ─ ┐  │  ┌──┐ 晴天                            FLAC · QQ        │
│    + 新建歌单 │  │晴│ 周杰伦                                              │
│              │  └──┘                                                  │
│ 我的音乐      │  ┌──┐ 夜曲                            MP3 · 酷我        │
│  ♡ 收藏       │  │夜│ 周杰伦                                              │
│  ◷ 最近播放   │  └──┘                                                  │
│  ☰ 播放列表   │                                                        │
│ 资源          │                                                        │
│  ▤ 本地库     │                                                        │
│  ↓ 下载       │                                                        │
│  ♪ 歌单       │                                                        │
│              │                                                        │
│  ⚙ 设置       │                                                        │
├──────────────┴────────────────────────────────────────────────────────┤
│ ┌────┐ 晴天        ↻  ⏮  (▶)  ⏭        [☰]  [🔊 ──●──]  [词]        │ 88
│ │封面│ 周杰伦·QQ     00:00 ────●──────────── 00:00                    │
│ └────┘ ♡  ⋯                                                          │
└───────────────────────────────────────────────────────────────────────┘
```

## 5. 分批改造清单

### 第一批：骨架与观感（本次执行）

- [x] **P1-1 主题换绿**（`shiyin/app/ui/theme.py`）
  - 重写 `LIGHT`：新色板、无边框列表、胶囊搜索框、圆形播放键、极简滚动条、菜单样式。
  - 新增对象名：`sidebar`、`searchInput`、`iconButton`、`playButton`、`lyricButton`、`navButton`、`dashedButton`、`shortcutButton`。
  - 验收：`stylesheet("light")` 含 `#2ecb71`，不再出现 `#0f9d90`（DARK 可保留）。

- [x] **P1-2 图标组件**（新增 `shiyin/app/ui/widgets/icons.py`）
  - QPainter 手绘 64×64 单色矢量图标：heart（描边/实心）、clock、list、folder、download、note、gear、search、play、pause、prev、next、queue、volume。
  - 不引入图片资源，打包体积不变；打包后不依赖额外文件。
  - 验收：各函数返回非空 `QIcon`，16/20/32 尺寸不糊。

- [x] **P1-3 播放条三段式**（`shiyin/app/ui/widgets/player_bar.py`）
  - 左 240px：56 封面 + 歌名 15/歌手 12 + ♡ 收藏 + ⋯ 菜单（加入歌单…）。
  - 中：循环 · 上一首 · 44px 圆形播放 · 下一首；下方整宽进度条 + 两端时间。
  - 右 210px：队列、音量（84px 滑块）、歌词「词」。
  - 删除整栏绿色 `paintEvent` 填充，缓冲改为进度槽底部 2px 细线。
  - 页面上所有既有控件/槽函数复用：`toggle/previous/next/seek/set_volume/cycle_repeat`。
  - ♡ 直接调 `repository.is_in_playlist/add_to_playlist/remove_from_playlist`（已有接口）。
  - 验收：点播放键仍切换播放/暂停；进度点击仍跳转；音量点击仍跳转且防抖落盘；空白区点击仍开关歌词页。

- [x] **P1-4 左侧分组导航**（`shiyin/app/ui/mainwindow.py`）
  - 侧栏 232px、`#f7f7f7`、右侧 1px 分隔；品牌行（绿色圆角 logo + 拾音）。
  - 两个方形快捷入口（收藏 / 队列）+ 虚线「＋ 新建歌单」（复用 `create_playlist()`）。
  - 分组标题「我的音乐」「资源」作为不可选列表项；6 个页面项带图标（设置固定在底部，不在列表里）；选中态=3px 绿竖条 + 浅灰圆角底。
  - 「设置」固定在侧栏底部。
  - 导航行号与页面索解脱钩：item 存 key，`_show_page()` 统一管 stack/高亮/历史/刷新；前进后退改用 `_select_nav()`。
  - 验收：7 个页面均可达（6 个列表项 + 底部设置按钮）；前进/后退仍正确；搜索页无高亮；设置按钮高亮只在设置页。

- [x] **P1-5 列表去边框 + 行内封面**（`shiyin/app/ui/models/track_model.py`、新增 `shiyin/app/ui/widgets/view_style.py`；第二批已由 `widgets/track_list.py` 取代）
  - `DecorationRole` 为第 0 列生成 40×40 圆角色块 + 首字（颜色按标题哈希取 6 色之一）。
  - `style_track_view()`：关斑马纹、关网格、无边框、隐藏表头、行高 64、图标 40、滚动按像素。
  - 收藏/最近/队列/本地库/搜索/歌单 6 个表统一套用；下载表去网格去斑马纹、保留表头、行高 52。
  - 验收：6 个页面行高 64、表头隐藏、`alternatingRowColors()==False`；播放条封面逻辑不受影响。

- [x] **P1-6 顶栏**（`mainwindow.py`）
  - 64px；后退/前进 32px；新增刷新（`_refresh_current()`：列表页 reload，搜索页按上次关键词重搜）。
  - 搜索框 36px 胶囊、内嵌放大镜、最大 420。

- [x] **P1-7 回归验证**
  - `tests/test_core.py` 21 例通过；`scripts/smoke_ui.py` 改为按 key 切页后通过。
  - 扩展离屏冒烟 40 项全过：6 个导航项 + 底部设置、2 个分组标题、侧栏 232 / 顶栏 64 / 播放条三段 240 · 弹性 · 210、
    ♡ 收藏切换、行高 64 + 表头隐藏、音量与进度点击、缓冲反馈、列宽比例（960 宽无横向滚动条）。
  - 截图：`%TEMP%\shiyin_after.png`（离屏，仅能验布局）+ `%TEMP%\shiyin_after_fonts_1180.png`、`%TEMP%\shiyin_after_fonts_960.png`（真实字体，目检通过）。
  - 打包：`重新打包.bat`，产物 `dist\ShiYin\`。

### 第二批：信息层级（已完成）

- [x] **P2-1 统一页头**（新增 `widgets/page_header.py`）
  - `PageHeader(title, subtitle)`：左侧 20px 标题 + 12px 灰副标题竖排，右侧 `actions` 放操作按钮；
    `add_action()` 生成 ghost/primary 按钮，`set_title()` / `set_subtitle()` 动态更新，空副标题自动隐藏。
  - 收藏 / 最近 / 队列 / 本地库 / 歌单 / 搜索 / 设置 7 个页面全部替换（下载页保留进度表头，未动）。
  - 空状态：`TrackListView.empty_text` 在列表无数据时居中画提示（两行文案）。
  - 验收：7 个页面 `isinstance(page.header, PageHeader)`；按钮全部搬到页头右侧，原槽函数名不变。

- [x] **P2-2 行内两行文本**（新增 `widgets/track_list.py`）
  - `TrackListDelegate` 自绘 64px 行：40px 首字封面、歌名 15 `#1f2937` + 歌手 12 `#8a8f99` 上下两行，
    右侧 200px 内显示「时长 · 音质 · 来源」，全部 `elidedText` 防溢出；选中浅绿圆角 + 3px 绿竖条，hover 浅灰。
  - `TrackListView` 继承 `QListView`，提供 `select_row()` / `selected_rows()` / `empty_text`；
    `style_track_list()` 统一去边框、关横向滚动、按像素滚动、单选/多选、`UniformItemSizes`。
  - 6 个曲目页（收藏 / 最近 / 队列 / 本地库 / 搜索 / 歌单）由 `QTableView` 换为 `QListView`，属性 `table` → `list`。
  - 验收：6 页 `itemDelegate()` 为 `TrackListDelegate`，行高 64，960 宽无横向滚动条。

- [x] **P2-3 搜索页结果区**：结果统计并入页头副标题（「共 N 条 · 用时 X ms」，搜索中显示进度）；
  音源错误折叠为页头右侧「N 个源未响应 ▾」链接按钮，点开 `QMenu` 逐源列出错误，不再占一行。
- [x] **P2-4 设置页分区**：目录与下载 / 搜索与缓存 / 音源三张 `QFrame#settingsCard` 白卡（P3-3 追加「外观」为第 3 张，共 4 张），表单与音源树放进 `QScrollArea`；
  保存按钮移到页头右侧。

### 第三批：可选增强（已完成）

- [x] **P3-1 队列右侧抽屉**（`mainwindow.py`）
  - 内容区右侧滑出 `QFrame#queueDrawer`，固定宽 380，从顶栏下沿到播放条上沿；
    180ms `QPropertyAnimation` 滑入、160ms 滑出，带左侧投影，`eventFilter` 跟随窗口缩放贴右。
  - 抽屉内是**第二个 `QueuePage` 实例**（同一个 `QWidget` 不能同时挂在 stack 与抽屉里），
    隐藏页面原页头，改用「播放队列 · N 首 · 第 i 首 + 清空 + ×」紧凑标题行；双击切歌、右键菜单、清空全部可用。
  - 播放条 `☰` 改为开关抽屉（原先跳转「播放列表」页）；左侧导航里的播放列表页与历史栈保持不变。
  - 打开歌词页时自动收起抽屉；再次点 `☰` 或 `×` 收起。
  - 验收：抽屉宽 380、右边缘贴合窗口、960 宽下仍贴右、导航播放列表页仍在。

- [x] **P3-2 真实封面接入**（`models/track_model.py` + `track_list.py` + `player_bar.py`）
  - `track_cover_pixmap(track, size)`：先查 `covers_dir/cover_<id 哈希>.jpg`，再读本地音频内嵌封面
    （MP3 APIC / FLAC picture / MP4 covr / Ogg base64 picture），抽到即落盘复用；
    没有封面才回退到首字色块，**只在有封面时覆盖**。
  - 居中裁成方图 + 8px 圆角，列表 40px、播放条 56px 同步换用；在线曲目仍用首字色块，不做网络抓图。
  - 无封面曲目做负缓存，避免每次重绘都重新读标签；切换主题/更换目录可清缓存。
  - 验收：covers 目录放图后列表与播放条都显示真图；移除后回退首字色块；合成 APIC 的 MP3 能抽出 885B JPEG。

- [x] **P3-3 深色主题开关**（`theme.py` + `settings_page.py` + `mainwindow.py`）
  - `stylesheet("dark")` 启用完整 DARK（与 LIGHT 同步覆盖 sidebar/topbar/pageTitle/cardTitle/
    settingsCard/sidePanel/playlistList/queueDrawer 等第三批全部 objectName，含 `QLabel` 透明）。
  - 设置页新增「外观」卡片，下拉「浅色/深色」切换后**立即生效并写入 `config.json` 的 `theme`**，重启沿用。
  - 自绘部分同步换色：列表 delegate（选中 `#1c2a2e`、正文 `#f1f3f5`、次要 `#9aa4b2`）、
    空态文字、播放条图标、导航/快捷入口/搜索图标按主题重新生成。
  - 验收：设置页下拉切深色后 `_theme == dark`、样式表含 `#14161a`、配置写回；切回浅色恢复。

### 第四批：试听缓冲反馈（体验修复，已完成）

用户反馈：双击搜索结果的在线歌曲试听时没有缓存动画，听感上要等几秒。侦察后定位到两个机制：

- `PlaybackService._resolve_target()` 只认 `entry.done`（整首缓存完成）才返回播放路径，而等待期间 UI 没有可见反馈。
- 播放条缓冲线用父窗口 `paintEvent` 画在 `QSlider` 底层，被滑块背景整块盖住；且 `mapTo` 第二参数
  传了 `geometry.topLeft()`，偏移量加两遍，线实际画到播放栏外。
- 中途试过把 `.part` 通过本地 HTTP 代理交给 Qt 边下边播：真实 `QMediaPlayer` 能 0.2s 出声，但下载线程
  重试、临时文件改名、服务端提前结束都会让 Qt 收到截断流，实测出现无法播放/只播约 30s 等不稳定现象。
  **最终回退为完整缓存后播放**，牺牲一点首声时间换稳定性。

- [x] **P4-1 在线试听改为完整缓存后播放**（`services/playback_service.py`）
  - `_resolve_target()` 登记缓存后，未完成时返回空并登记 `_pending_entry`，不再返回流代理 URL；
    `QTimer` 每 100ms 检查 `entry.done`，完成且 `final_path` 存在后才 `backend.load(final_path)`。
  - `_play_token` 防止“上一首的缓存完成后把新歌顶掉”；切换歌曲/清空队列/停止播放都会取消等待。
  - 180s 超时、`entry.error`、`entry.cancelled`、缓存文件丢失都会停止等待并发出 `failed`，不会再无限转圈。
  - 完成后再做完整性校验：`mutagen` 时长明显短于搜索结果标注时长，或“时长 × 实际码率”估算的字节数远大于文件大小（MP3 截断但 Xing 头仍保留完整时长）时，判定为 30s 试听/截断；有 `alternatives` 就自动切备选源，没有则明确提示。
  - 本地文件与已完整缓存仍直接返回路径，无额外等待。

- [x] **P4-2 可见的缓存反馈**（新增 `widgets/buffer_spinner.py`，改 `widgets/player_bar.py`）
  - 只保留播放键上覆盖的白色 300° 旋转弧线（16ms 转 12°）和左侧「缓存中 N%」；**不画进度条底部缓冲线**（与百分比/转圈重复且容易误导）。
  - `playing` 时强制把缓存进度记为 100%、停止转圈并恢复「歌手 · 音源」；播放器在已出声后短暂进入 `BufferingMedia` 时，若 `backend.is_playing()` 为真则不重新启动转圈，修复“歌在放、按钮是暂停、转圈不停”。
  - 缓存完成但播放器尚未 `playing` 的短暂间隙也会收转圈，避免停在 99% 转个不停。
  - `failed` 的原因（残缺音源、无备选源、超时）显示在歌手行并写 tooltip，避免“点歌没反应/只播 30s”没有任何解释。
  - 验收：浅色/深色 1180×760 截图只显示转圈 + 百分比；扩展冒烟 69/69（含音量/进度点击）；状态序列探针通过。

- [x] **P4-3 播放键状态同步 + 滑块去灰底**（改 `core/audio_backend.py`、`ui/widgets/player_bar.py`、`ui/theme.py`）
  - 根因：已经出声后 Qt 仍可能发 `BufferingMedia`，`AudioBackend` 把内部状态从 `playing` 改成 `buffering`；`PlayerBar._on_state` 的 `else` 分支又把按钮画成“播放”图标。点一次按钮时 `playbackState` 真正变化，才重新同步。
  - `AudioBackend._on_status()`：只有播放状态不是 `PlayingState` 时才上报 `buffering`；`Playing` 中的 `BufferingMedia`/`StalledMedia` 不再改状态。
  - `PlayerBar._on_state()`：`playing` 画暂停键，`paused`/`idle`/`failed` 画播放键，`loading`/`buffering` 保持当前图标，不再误把播放键改回三角形。
  - `theme.py`：`QSlider` 本体、`groove`、`add-page` 全部透明，只保留绿色 `sub-page` 和手柄；播放进度条与音量条不再有浅灰长方块底色（浅色/深色都改）。
  - 验收：状态探针 `playing → buffering` 后 tooltip 仍为「暂停」；播放中截图按钮为暂停图标，进度/音量条无灰色底。

- [x] **P4-4 下载曲目进度/歌词加载修复**（改 `services/library_service.py`、`data/repository.py`、`ui/widgets/player_bar.py`）
  - 现象：下载完成的歌曲出现在本地库后，双击播放时音频正常出声，但进度条停在 0、歌词页显示「暂无歌词」。
  - 根因一：下载注册的是在线曲目（带 `lyric_path`），本地库扫描又按指纹生成一条 local 记录；用户双击 local 记录时，原 `.lrc` 没有被写进该记录，`lyric_path` 为空。
  - 根因二：部分本地文件/后端组合没有稳定发 `durationChanged`，或者位置信号偶发断掉；PlayerBar 的 `_loading` 一直为 True，`_on_position` 被挡住，界面永远 00:00。
  - `LibraryService.read_lyric()`：扫描/导入时读取同目录 `.lrc`（UTF-8/UTF-8-SIG/GB18030），写入 `lyric_path`；已存在的 local 记录命中指纹时只补歌词，不重复入库。
  - `Repository.find_by_path()`：下载注册过的同一路径不再被扫描成第二条 local 曲目；`_row_to_track()` 对老记录兜底读同目录 `.lrc`，已有历史记录无需删库重扫。
  - `PlayerBar`：本地曲目在 `_on_track()` 先用 `track.duration_ms` 画时长；新增 250ms 位置轮询，若 `durationChanged` 没来或位置信号断掉，用 `backend.position()` 兜底推进进度。
  - 验收：离线探针 `%TEMP%\shiyin_local_progress_probe2.py` 中 `dur=04:29`、进度从 `00:00` 走到 `00:03` 且 slider 同步；`shiyin_lyric_scan_probe.py` 扫描含 `.lrc` 的文件后 `lyric_len=1210`；单测 21/21、仓库冒烟通过、扩展冒烟 69/69。
  - 打包：为避免覆盖用户正在运行的 `dist\ShiYin\ShiYin.exe`（PID 14216），本轮先构建到 `dist_patch\ShiYin\ShiYin.exe`（12,614,948 B @ 2026-11-07 23:33:28），`--selftest` exit 0；关闭旧实例后再替换 `dist\ShiYin`。

### 第五批：使用状态记忆与启动扫描（已实施 2026-11-07）

> 用户已拍板三项：① 恢复会话默认暂停；② 启动扫描 `library_dir + download_dir`；③ canonical 空库时自动恢复项目根旧库，先备份。以下保留原计划，执行结果见 P5-5。

#### P5-0 现状诊断（本轮只读检查的结果）

| 检查项 | 实测 |
|---|---|
| 打包版/源码默认数据目录 | `C:\Users\HP\AppData\Local\ShiYin`（无 `portable.flag` 时统一走这里） |
| 当前 AppData 数据库 | P5 规划时 0 首；本轮下载后已有 8 首本地曲目，但收藏/最近播放仍为空 |
| 项目根旧数据库 | `ShiYin-Source-0.1.0\data\library.db` 有 **3 首本地曲目、4 条最近播放**，无收藏 |
| 配置的本地库目录 | `C:\Users\HP\AppData\Local\ShiYin\library`（10 个音频/歌词文件，其中 5 首有 `.lrc`） |
| 配置的下载目录 | `D:/Users/HP/Music` |
| 播放队列/当前歌曲 | `PlaybackService` 只在内存里，启动时为空；`PlayerBar` 初始为「未在播放」 |
| 本地库启动行为 | `LibraryPage.reload()` 只查数据库，不扫描目录；扫描只能点「扫描目录」手动触发 |

结论：收藏和最近播放本身有 SQLite 表与写入逻辑，当前看到空白不是页面没刷新，而是**打开时连到了一份空库**；旧记录在项目根另一份库。队列、当前歌曲、播放位置则完全没有落盘。

#### P5-1 数据落点统一与旧库恢复（先修“为什么空白”）

- 保持现有目录策略，不擅自把 AppData 搬到安装目录：
  - 普通安装/打包版：`%LOCALAPPDATA%\ShiYin`；
  - 存在 `app_root()/portable.flag`：`app_root()/data`；
  - `SHIYIN_DATA_DIR` 仍可覆盖（测试用）。
- 启动时在日志和设置页显示实际 `data_dir` / `library.db` 路径，避免以后再出现“以为在写 A、其实打开的是 B”。
- 一次性旧库恢复（只在源码运行时有效，因为 `app_root()` 是源码根）：
  1. 打开 canonical DB 前检查 `app_root()/data/library.db`；
  2. 若 canonical DB 的 `tracks` 为 0、旧库非空：先备份两份 DB（`library.db.bak-时间戳`），再把旧库复制为 canonical DB；
  3. 若 canonical 已有数据：不覆盖，只在日志列出旧库曲目数，后续可另做“导入旧记录”按钮；
  4. 用 meta 键 `legacy_import_v1` 防止重复恢复。
- 不改表结构，不重写收藏/最近播放逻辑；补一条“收藏 → 重启 → 仍在”的回归用例。
- 验收：旧库恢复后最近播放 4 条可见；新收藏一首 → 关闭 → 重开 → 收藏仍为 1 条；日志明确打印 DB 路径。

#### P5-2 会话状态持久化（队列 / 当前歌曲 / 位置 / 页面）

- 复用现有 `meta(key, value)` 表，不新增表；在 `Repository` 增加 `get_meta()` / `set_meta()` 两个薄封装。
- 存储一个 `session.v1` JSON，字段固定：
  - `queue`：最多 1000 首；本地曲目存 `path`，在线曲目只存 `source/source_id/title/artist/album/duration_ms/ext/bitrate`，**不存会过期的 `url`/`raw`**；
  - `index`：当前队列下标；
  - `position_ms`：最后播放位置；
  - `page`：上次导航页 key（`favorites/recent/queue/library/...`，非法值回落收藏）；
  - `window`：可选，宽高 + 是否最大化；
  - `saved_at`：时间戳。
- 保存时机：
  - `queueChanged` / `currentChanged` 后 300ms 防抖写一次；
  - `positionChanged` 每 1s 节流写一次；
  - 暂停、切歌、清空队列、关窗/退出前立即 flush；
  - 恢复会话期间设 `_session_loaded=False`，避免启动时用空队列覆盖旧记录。
- 恢复时机与行为：
  - `MainWindow` 页面和 `PlayerBar` 都连好信号后再恢复，避免 `currentChanged` 丢给空 UI；
  - 队列、下标、当前歌曲恢复；**默认暂停，不自动出声**；
  - 本地/已缓存曲目：`backend.load()` 但不 `play()`，再 seek 到 `position_ms`；
  - 在线曲目：只恢复标题/歌手/封面与时长，不提前触发下载；点播放时重新 `adapter.resolve`；
  - 播放条显示上次歌曲与位置，按钮为「播放」；队列页和抽屉同步恢复；
  - 本地文件不存在、在线曲目无效：跳过并记日志，不阻塞启动。
- 可选开关：设置页「启动时恢复上次播放」默认开；「恢复后自动续播」默认关（推荐，避免一开软件就突然出声）。

#### P5-3 启动扫描本地库目录

- 启动完成后 `QTimer.singleShot(0, ...)` 在后台线程扫描，不阻塞窗口显示。
- 扫描范围：`settings.library_dir`；若 `download_dir` 存在且不是同一目录，也一并扫描（当前配置分别是 AppData\library 与 `D:/Users/HP/Music`）。**已拍板：两个目录都扫。**
- 复用 `LibraryService.scan()` 的指纹去重；第二次启动只统计 `skipped`，不会重复入库。
- 扫描细节：
  - 独立 SQLite 连接，避免主线程写收藏时和扫描线程抢同一个连接；
  - `on_progress` 每 100ms 更新一次「本地库：正在扫描 xxx（i/n）」，不弹窗；
  - 完成后 `LibraryPage.reload()` 并显示「新增 N，跳过 N，失败 N」；无变化时只更新副标题；
  - 目录不存在、无权限、单个文件损坏都只记日志，不中断整次扫描。
- 设置页增加「启动时扫描本地库」开关，默认开；关闭后仍保留手动「扫描目录」。

#### P5-4 设置项、验收与边界

- 设置页新增「启动与记忆」卡片：
  - 启动时恢复上次播放（默认开）
  - 恢复后自动续播（默认关）
  - 启动时扫描本地库（默认开）
  - 只读显示「数据目录 / 数据库 / 本地库目录」，附「打开目录」按钮
- 验收：
  1. 单测：session JSON 往返；队列/下标/位置/页面恢复；空队列不覆盖旧 session；在线 URL 不写入；
  2. 集成：临时数据目录 → 收藏 1 首 + 播放 1 首 + 队列 3 首 + 位置 30s → 关闭 → 重建 context → 收藏/最近播放/队列/当前歌曲/位置/页面全部恢复，且后端未自动 `play()`；
  3. 扫描：临时目录 2 首 + 下载目录 1 首 → 启动扫描后本地库 3 首；再启动一次 `skipped=3, added=0`；
  4. 旧库恢复：空 canonical + 旧库 3 首/4 条最近 → 恢复后数量一致，旧库和备份均保留；
  5. 回归：`compileall`、单测 21+、扩展冒烟 69+、浅色/深色截图、打包 `--selftest`。
- 本批明确不做：云同步/多用户 profile、账号登录、搜索历史、下载任务断点续传、把数据目录强行搬到安装目录、默认自动续播。
- 已确认的三个选择：
  1. 恢复会话**默认暂停**（`resume_autoplay=false`），不自动出声；
  2. 启动扫描 **`library_dir + download_dir`**（同目录自动去重）；
  3. 旧 `data\library.db` 在 canonical 为空时**自动恢复**，恢复前备份 canonical 与旧库，`meta` 标记 `legacy_import_v1` 防重复。

#### P5-5 实施结果（2026-11-07）

- 动手前备份：`backup\ShiYin-0.1.0_20261107-234512_P5\`（`shiyin\` + 本计划书，241 个文件）。
- `data/repository.py`：新增 `get_meta(key)` / `set_meta(key, value)`，复用现有 `meta` 表，不改 schema。
- `core/models.py`：新增 `Track.from_dict()`，只接收白名单字段，不恢复 `url` / `raw`。
- `services/settings_service.py`：`DEFAULTS` 新增 `startup_restore_enabled=True`、`resume_autoplay=False`、`startup_scan_enabled=True`；老 config 缺字段自动取默认。
- `services/session_service.py`（新建）：`session.v1` JSON 存队列（最多 1000 首）、当前下标、位置、页面、窗口宽高；`queueChanged/currentChanged` 后 300ms 防抖，位置 1s 节流，关窗/托盘退出前 `flush()`；恢复期间 `_loading=True` 不写，空队列且无操作不写，避免覆盖旧会话。
- `services/playback_service.py`：新增 `restore_state()`；本地曲目 `load_at` 后停在指定位置，在线曲目只恢复元数据、不提前下载；新增 `_loaded_track_id`，恢复的在线曲目点播放会先重新解析，而不是空放；在线恢复的位置会在缓存完成/直链加载后 seek 回去。
- `core/audio_backend.py`：新增 `load_at()`，等 `LoadedMedia` / `BufferedMedia` 后一次性 `setPosition`，避免 `setSource` 后立即 seek 被丢；恢复态明确发 `paused`。
- `ui/widgets/player_bar.py`：新增 `show_restored()`，恢复时收掉缓冲转圈、画时长/位置、按钮为播放键。
- `ui/mainwindow.py`：创建 `SessionService` 并 `bind_window`；页面切换 `note_page()`；启动时 `session.restore()`；`closeEvent` 与 `_force_quit()` 都 `flush()`；窗口显示后 `QTimer.singleShot(0, library_page.startup_scan)`。
- `ui/pages/library_page.py`：新增 `StartupScanWorker`（QThread + 独立 SQLite 连接，不调用会清理 `-wal` 的 `db.connect`），依次扫描 `library_dir`、`download_dir`，100ms 节流回报进度，完成后刷新列表并显示统计；设置关闭时跳过，手动扫描仍保留。
- `context.py`：新增 `_db_track_count/_db_meta/_sqlite_copy/_restore_legacy_db`；canonical 为空、旧库非空、无 `legacy_import_v1` 时，先备份 `library.db.bak-时间戳` 与 `library.db.legacy-bak-时间戳`，再通过 SQLite backup API + `os.replace` 落地；canonical 有数据绝不覆盖。**加护栏：只有默认数据目录且未设置 `SHIYIN_DATA_DIR` 时才尝试旧库恢复**，避免 UI 冒烟/测试的临时库被塞入旧曲目。
- `ui/pages/settings_page.py`：新增「启动与记忆」卡片（三个复选框 + 数据目录/数据库/本地库目录只读行与「打开」按钮），`save()` 写入三项开关；原卡片注释序号未改，实际为 5 张卡。
- 验证：
  - `compileall` exit 0；单测 `Ran 21 tests ... OK`；仓库冒烟通过；扩展冒烟 `共 69 项，通过 69，失败 0`。
  - `%TEMP%\shiyin_session_probe.py`：`session.v1` 往返成功，恢复队列 1 首、位置 30000ms、未自动 `play()`，JSON 内无 `url`/`raw`。
  - `%TEMP%\shiyin_session_ui_probe.py`：临时数据目录建 `MainWindow` → 写会话 → 关闭 → 重建 context/窗口；恢复页面 3、队列 1 首、播放条 `00:30`、后端 source 为本地文件。
  - `%TEMP%\shiyin_scan_ui_probe.py`：临时库目录放 1 首 flac，启动扫描后 `before 0 → after 1`，状态「新增 1，跳过 0，失败 0」。
  - `%TEMP%\shiyin_legacy_probe.py`：空 canonical + 旧库 3 首 → 恢复为 3 首，旧库仍 3 首，备份文件生成。
  - `%TEMP%\shiyin_loadat_probe.py`：真实 QMediaPlayer `load_at(30s)` 后 `position=30000`、内部状态 `paused`。
- 已知边界：窗口只恢复宽高，不恢复最大化；旧库恢复只对源码默认数据目录有效，打包版通常找不到项目根旧库（找不到自然跳过）；同一首晴天的两条历史记录（`local:a8d4f8ddfa3b75f2` / `f3cee7ca275c35e9`）尚未合并。

#### P5-6 会话丢失根因修复与回归（2026-11-08）

- 现象：用户实测 P5 重启后播放栏仍为空，在线/本地歌曲都没有上次播放信息。
- 诊断：P5 的 `session.v1` 确实写入了 `library.db-wal`，但 `shiyin/app/data/db.py` 的 `connect()` 每次启动都调用 `_clear_stale_journal()` 无条件删除 `library.db-wal` / `-shm` / `-journal`。上次运行已提交但尚未 checkpoint 的 `session.v1` 随 WAL 一起被删，所以下次启动读到的是“没有历史记录”。
- 修复：删除 `_clear_stale_journal()` 与调用，不再删除任何 journal 边车文件；连接成功后对 WAL 执行 `PRAGMA wal_checkpoint(TRUNCATE)`，把上次运行留在 WAL 里的已提交数据合并回主库，交给 SQLite 自己恢复。
- 加固：`SessionService._ready` 初值改为 `True`（第一次播放即能落盘）；`restore()` 的“设置关闭 / 没有历史记录 / 历史队列为空”三条早退分支补日志；`_on_current_changed` 立即 `flush()` 一次，不等 300ms 防抖；首次成功写入打印“会话已写入：队列 N 首，当前位置 …，页面 …”。
- 升级兜底：无 `session.v1`（旧版本升级第一次启动）时，用 `playlist_tracks("recent")` 的最后一首填回播放栏，只恢复为暂停态、位置 0、不自动播放；下一次正常关窗后会写成正式 `session.v1`。
- 验证：
  - `compileall` exit 0；单测 21/21；仓库冒烟通过；扩展离屏冒烟 `共 69 项，通过 69，失败 0`。
  - 临时数据目录强制结束进程后重启：`会话恢复：无 session.v1，已用最近播放兜底：晴天` → `会话已写入` → 强制结束 → 重启 `已恢复会话：队列 1 首，当前第 1 首，位置 0.0s，页面 favorites`。
  - 真实 `%LOCALAPPDATA%\ShiYin`：最终版启动日志为 `已恢复会话：队列 1 首，当前第 1 首，位置 0.0s，页面 favorites`，窗口标题 `晴天 - 拾音`；不再出现“无 session.v1”。
  - `dist\ShiYin\ShiYin.exe` 最终版 12,633,064 B @ 2026-11-08 12:59:20；`--selftest` returncode 0。
- 说明：用户在 P5 构建后没有播放过歌，因此第一次打开没有可恢复的 P5 会话属于正常；本轮用“最近播放兜底”完成升级迁移，之后按真实播放/关窗写入的位置恢复。

## 6. 不做清单（明确排除）

登录 / VIP / 会员中心 / 推荐卡片 / 歌单广场 / 电台 / 音质切换 / 倍速 / 评论 / 分享 / MV；
不改导航页面数量与顺序含义；不改 repository 现有方法语义、adapter、数据库 schema；
P4 只调整 `PlaybackService` 的在线试听加载路径与播放条反馈，不改队列/收藏/下载/搜索的接口与行为。
P5 只增加启动恢复与启动扫描；复用现有 `meta` 表与 `Repository` 新增读取封装，不新增表、不迁移/删除用户数据、不默认自动续播。
不引入第三方 UI 库、不引入图标字体、不新增运行时资源文件。

## 7. 验证与交付

1. 核心单测：`.venv\Scripts\python.exe -m unittest discover -s tests -p "test_core.py"`
2. 仓库冒烟：`.venv\Scripts\python.exe scripts\smoke_ui.py`（需同步改为按 key 切页）
3. 离屏 UI 冒烟：`%TEMP%\shiyin_ui_smoke.py`（扩展后全过）
4. 截图目检：offscreen `w.grab().save(path)`
5. 打包：`重新打包.bat`，产物 `dist\ShiYin\`

失败回滚：从备份 `source\` 覆盖回项目目录（不要覆盖 `data\`、`.venv`、`dist`）。

## 8. 风险点与对策

| 风险 | 对策 |
|---|---|
| 导航行号与 stack 索引脱钩后前进/后退错位 | `_show_page()` 单点入口 + 冒烟逐页往返验证 |
| 全局 QSS 影响设置页表单/树 | 只对 `QListView`/`QTableView`/`QListWidget#nav`/指定 objectName 生效；卡片内 `QLabel` 统一透明，表单控件保留圆角 8 |
| 播放条 88px 内塞三段导致 960 宽拥挤 | 左 240 / 右 210，中间弹性最小约 240；最小窗口下截图确认 |
| 缓冲动画删除后被当成功能缺失 | P4 用播放键白色转圈 + 「缓存中 N%」两处反馈；进度条底部线已按反馈删除，避免冗余 |
| 把下载中的 `.part` 直接交给 Qt 边下边播 | 已回退：下载重试/改名/源提前结束会让 Qt 收到截断流（无法播放或只播约 30s）；只在 `entry.done` 后播 `final_path` |
| 已出声后 Qt 媒体状态短暂 `BufferingMedia` | 之前会把内部状态改成 `buffering`，界面把播放键画成“播放”，点一次才恢复；现在 `AudioBackend` 仅在未 Playing 时上报 `buffering`，`PlayerBar` 的 `loading/buffering` 不再改播放图标 |
| 音源实际只有约 30s 试听/文件被截断但 `entry.done=True` | 播前用 `mutagen` 时长和码率估算字节数校验；不合格自动切 `alternatives`，无备选源时明确提示，不静默播 30s |
| 首字色块在无 QApplication 环境下崩溃 | 只在实际绘制（DecorationRole）时生成，单测不触达 |
| 旧库恢复覆盖现有数据 | 仅在 canonical `tracks=0` 且旧库非空时执行；先备份两份 DB，`meta` 标记只做一次；canonical 有数据绝不覆盖；且只在默认数据目录、未设 `SHIYIN_DATA_DIR` 时尝试，避免污染临时测试库 |
| 启动扫描卡住界面/与收藏写入抢锁 | 后台线程 + 独立 SQLite 连接、进度节流、单文件失败不影响整次；设置页可关闭 |
| 恢复会话时把空队列写回、覆盖上次记录 | 恢复期间 `SessionService._loading=True`、`_ready=False`，恢复完成前不触发保存；空队列且无操作不写；退出/切歌前显式 flush |
| 启动自动出声惊吓用户 | 默认只恢复暂停态，不调用 `play()`；自动续播作为单独开关且默认关 |
| 在线 URL 过期仍被恢复 | session 不存 `url`/`raw`，只存 source/source_id 等元数据，点播放时重新解析 |
| 队列过大导致 session JSON 膨胀 | 最多持久化 1000 首；超出截断并写日志，当前内存队列不受影响 |
| 多份数据目录让用户越用越乱 | 启动日志和设置页固定显示 data_dir/db/library_dir；不静默搬目录，只在源码根发现旧库时一次性恢复 |

## 9. 进度记录

| 日期 | 事项 | 结果 |
|---|---|---|
| 2026-11-07 | 备份 + 哈希校验 | 160 文件 0 差异（`backup\ShiYin-0.1.0_20261107-181717`） |
| 2026-11-07 | P1-1 主题换绿 `theme.py` | 完成，`stylesheet("light")` 含 `#2ecb71`、不含 `#0f9d90` |
| 2026-11-07 | P1-2 图标组件 `widgets/icons.py` | 完成，15 个 QPainter 图标 + `NAV_ICONS`，无外部资源 |
| 2026-11-07 | P1-3 播放条三段式 `player_bar.py` | 完成，左 240 / 中弹性 / 右 210，♡ 收藏、⋯ 菜单、词入口、缓冲细线 |
| 2026-11-07 | P1-4 左侧分组导航 `mainwindow.py` | 完成，`NAV_GROUPS` + `_nav_pages` + `_show_page()`，行号与页面索引解耦 |
| 2026-11-07 | P1-5 列表去边框 + 行内封面 `track_model.py` / `widgets/view_style.py` | 完成，6 页统一 64 行高、隐藏表头、40px 首字封面、列宽按视口比例分配（第二批已改由 `track_list.py` 绘制） |
| 2026-11-07 | P1-6 顶栏 | 完成，64px、后退/前进/刷新、36px 胶囊搜索框 |
| 2026-11-07 | P1-7 回归 | `compileall` 通过；单测 21/21；仓库冒烟通过；扩展离屏冒烟 40/40 |
| 2026-11-07 | 验证期发现并修复 | ① 缓冲线用子控件相对坐标画到了歌名上 → `mapTo()` 换算；② 「词」按钮被通用 `QPushButton` 的 `padding:6px 14px` 裁成一个偏旁 → 补 `padding:0`；③ 960 宽下列表出现横向滚动条 → 列宽改为按视口比例分配 |
| 2026-11-07 | 真实字体截图目检 | 1180 与 960 两种尺寸布局正常（离屏平台 `families()==0`，中文只能靠真实字体截图验） |
| 2026-11-07 | P1-7 重新打包 | `dist\ShiYin\ShiYin.exe` 12,566,736 B；PyInstaller 223.8s 构建成功，无 ERROR |
| 2026-11-07 | 打包版自检 | `ShiYin.exe --selftest` 8s 退出码 0，`%LOCALAPPDATA%\ShiYin\logs\shiyin.log` 仅记录正常启动 |
| 2026-11-07 | P2-1 统一页头 `widgets/page_header.py` | 完成，7 个页面替换；空状态由 `TrackListView.empty_text` 居中绘制 |
| 2026-11-07 | P2-2 两行列表 `widgets/track_list.py` | 完成，6 页 `QTableView` → `QListView` + 自绘 delegate（64 行高 / 40 封面 / 15+12 两行） |
| 2026-11-07 | P2-3 搜索页结果区 | 完成，统计并入副标题，「N 个源未响应 ▾」折叠菜单 |
| 2026-11-07 | P2-4 设置页分区 | 完成，三张白卡 + `QScrollArea`，保存按钮移到页头 |
| 2026-11-07 | P2 回归 | `compileall` 通过；单测 21/21；仓库冒烟通过；扩展离屏冒烟 56/56 |
| 2026-11-07 | P2 验证期发现并修复 | ① `QListView` 下 `selectedRows()` 返回空（SelectRows 跨列）→ 新增 `selected_rows()` 按首列过滤 `selectedIndexes`；② 卡片内 `QLabel` 被全局 `QWidget` 背景涂成灰块 → 全局 `QLabel { background: transparent }`；③ 歌单左栏三个按钮补 `panelButton` 边框样式 |
| 2026-11-07 | P2 真实字体截图目检 | 收藏 1180/960、本地库 960、队列 960、设置 1180/960、搜索 1180、歌单 1180 布局正常，窄窗口无横向滚动条 |
| 2026-11-07 | P2 重新打包 | `build_whitelist.py --check` 通过；PyInstaller 192s 构建成功，`dist\ShiYin\ShiYin.exe` 12,572,289 B |
| 2026-11-07 | P2 打包版自检 | `ShiYin.exe --selftest` 退出码 0（19:37:44 启动日志正常，无异常） |
| 2026-11-07 | P3-1 队列右侧抽屉 | 完成，380px 滑入层 + 第二个 QueuePage 实例 + 紧凑标题行，跟随缩放贴右；导航页保留 |
| 2026-11-07 | P3-2 真实封面接入 | 完成，covers 目录 / 内嵌 APIC·FLAC·MP4·Ogg，抽到落盘；列表 40 / 播放条 56；无封面才回首字块 |
| 2026-11-07 | P3-3 深色主题开关 | 完成，设置页「外观」下拉即时切换并记忆，DARK 补齐全部新 objectName 与自绘颜色 |
| 2026-11-07 | P3 回归 | `compileall` 通过；单测 21/21；仓库冒烟通过；扩展离屏冒烟 69/69 |
| 2026-11-07 | P3 验证期发现并修复 | 抽屉原先用 `centralWidget()` 尺寸定位，窗口未 show 时仍是 640×480，抽屉被放到内容区左侧且高度截半 → 改用主窗口 `width()/height()` |
| 2026-11-07 | P3 真实字体截图目检 | 浅色/深色收藏页、浅色/深色抽屉（1180 + 960）、深色设置页布局正常，窄窗抽屉贴右 |
| 2026-11-07 | P3 内嵌封面实测 | 本地 flac/mp3 本身无内嵌图（0 字节）；给 MP3 合成 APIC 后成功抽出 885B JPEG，证明提取分支可用 |
| 2026-11-07 | P3 重新打包 | `build_whitelist.py --check` 通过；PyInstaller 197s 构建成功；`dist\ShiYin\ShiYin.exe` 12,608,389 B（新增 mutagen 格式子模块） |
| 2026-11-07 | P3 打包版自检 | `ShiYin.exe --selftest` 退出码 0（20:11:42 启动日志正常，无异常） |
| 2026-11-07 | P4-1 完整缓存后播放 | 先用真实 QMediaPlayer 验证 `.part` 边下边播能 0.2s 出声，但重试/改名/截断会导致无法播放或只播约 30s；已改为 `QTimer` 等 `entry.done` 再播 `final_path`，带 token 防串歌与 180s 超时 |
| 2026-11-07 | P4-1 稳定链路探针 | 512KB 慢速 HTTP 源：`loaded_immediately=[]`，1.01s 后加载的是 `...\a48c1ed220bad500.mp3`（`entry.done=True`），没有把 `http://` 交给播放器 |
| 2026-11-07 | P4-1 残缺音频识别 | `mutagen` 时长 + “时长 × 实际码率”字节估算：完整 9.84MB MP3 通过；截断到 1MB 的同一 MP3 被判定为截断并提示/切备选源 |
| 2026-11-07 | P4-2 缓冲反馈 | 只保留播放键白色旋转弧线 + 「缓存中 N%」；不再画进度条底部缓冲线；`playing` 后强制 100% 并收转圈 |
| 2026-11-07 | P4-2 状态机探针 | 模拟 `buffering → playing → buffering`：`playing` 后 `_buffering_ui_active=False`、进度 100%、转圈隐藏，后续 `buffering` 不重启转圈 |
| 2026-11-07 | P4-3 播放键图标同步 | 状态探针中 `playing` 后 tooltip 为「暂停」，紧随其后的 `buffering` 仍保持「暂停」，不再点一次才恢复 |
| 2026-11-07 | P4-3 后端状态守卫 | `PlayingState` 下的 `BufferingMedia`/`StalledMedia` 不再把内部状态改成 `buffering` |
| 2026-11-07 | P4-3 滑块去灰底 | `QSlider` 本体、`groove`、`add-page` 透明，只留绿色进度与手柄；播放中截图确认进度/音量无浅灰长方块 |
| 2026-11-07 | P4 回归 | `compileall` 通过；单测 21/21；仓库冒烟通过；扩展离屏冒烟 69/69 |
| 2026-11-07 | P4 截图目检 | `%TEMP%\shiyin_buffer_ui_1180_light.png` / `_dark.png`：只显示转圈 + 百分比，无底部缓冲线 |
| 2026-11-07 | P4 重新打包 | `build_whitelist.py --check` 通过；PyInstaller 构建成功；`dist\ShiYin\ShiYin.exe` 12,612,698 B（22:56:54） |
| 2026-11-07 | P4 打包版自检 | `ShiYin.exe --selftest` 退出码 0（重建后启动日志正常，无异常） |
| 2026-11-07 | P5 使用状态记忆计划 | 已写入本计划书「第五批」；用户批准三项默认选择后进入实施 |
| 2026-11-07 | P5-1 旧库恢复 + 数据路径日志 | 空 canonical 时备份两份并恢复旧库；`legacy_import_v1` 防重复；临时数据目录加护栏，冒烟不再被污染 |
| 2026-11-07 | P5-2 会话持久化 `session_service.py` | 队列/下标/位置/页面写 `meta.session.v1`；默认暂停恢复，在线曲目不存 URL；窗口关闭/托盘退出 flush |
| 2026-11-07 | P5-3 启动扫描 `library_page.py` | 后台线程 + 独立连接扫 `library_dir + download_dir`，100ms 节流，完成刷新并统计新增/跳过/失败 |
| 2026-11-07 | P5-4 设置卡片 | 「启动与记忆」三项开关 + 数据目录/数据库/本地库目录只读行；老 config 缺键取默认 |
| 2026-11-07 | P5 回归 | `compileall` 通过；单测 21/21；仓库冒烟通过；扩展离屏冒烟 69/69；会话往返/窗口重建/启动扫描/旧库恢复/真实 seek 探针全通过 |
| 2026-11-07 | P5 设置页目检 | `%TEMP%\shiyin_p3_settings_1180_light.png`：「启动与记忆」卡片三项开关、三行只读路径与「打开」按钮布局正常，1180 宽无截断 |
| 2026-11-07 | P5 重新打包 | `build_whitelist.py --check` 通过；PyInstaller 164s 构建成功；`dist\ShiYin\ShiYin.exe` 12,631,971 B（2026-11-08 00:10:22）；`--selftest` 退出码 0 |
| 2026-11-07 | P4-4 下载曲目进度/歌词修复 | 本地扫描补 `.lrc`、老记录兜底读歌词、同路径去重；PlayerBar 本地时长兜底 + 250ms 位置轮询；单测 21/21、冒烟 69/69 |
| 2026-11-08 | P5 会话丢失根因 | `db.connect()` 每次启动删 `library.db-wal`，把未 checkpoint 的 `session.v1` 一并删掉；改为保留 WAL + 连接后 `wal_checkpoint(TRUNCATE)` |
| 2026-11-08 | P5 会话加固 | `_ready=True` 初值；早退分支日志；当前曲目立即 flush；首次写入日志；无会话时用最近播放兜底，暂停态位置 0 |
| 2026-11-08 | P5 会话回归 | 单测 21/21、扩展冒烟 69/69；临时库强制结束进程后重启恢复成功；真实库启动日志 `已恢复会话：队列 1 首，当前第 1 首，位置 0.0s，页面 favorites` |
| 2026-11-08 | P5 最终打包 | `dist\ShiYin\ShiYin.exe` 12,633,064 B @ 12:59:20；`--selftest` returncode 0 |

> 验证命令（PowerShell）：
> `$env:QT_QPA_PLATFORM='offscreen'; .venv\Scripts\python.exe -m unittest discover -s tests -p "test_core.py"`
> `.venv\Scripts\python.exe scripts\smoke_ui.py`
> `.venv\Scripts\python.exe %TEMP%\shiyin_ui_smoke.py`
>
> 截图脚本（不设 offscreen，直接 `w.grab()`）：`.venv\Scripts\python.exe %TEMP%\shiyin_shot2.py <宽> <高> <favorites|settings|search|playlists|library|queue|drawer> <light|dark>`
>
> 第二批截图：`%TEMP%\shiyin_p2_favorites_1180.png` / `_960.png`、`shiyin_p2_settings_1180.png` / `_960.png`、`shiyin_p2_search_1180.png`、`shiyin_p2_playlists_1180.png`、`shiyin_p2_library_960.png`、`shiyin_p2_queue_960.png`
>
> 第三批截图（`shiyin_shot2.py <宽> <高> <页面> <light|dark>`）：`shiyin_p3_favorites_1180_light/dark.png`、`shiyin_p3_drawer_1180_light/dark.png`、`shiyin_p3_drawer_960_light.png`、`shiyin_p3_settings_1180_dark.png`
>
> 第四批缓冲态截图（`shiyin_buffer_shot.py 1180 760 <light|dark>`）：`%TEMP%\shiyin_buffer_ui_1180_light.png`、`%TEMP%\shiyin_buffer_ui_1180_dark.png`

### 后续观察（未做）

- 第三批 P3-1 ~ P3-3、第四批 P4-1/P4-2 已完成并打包；真实网络音源试听、托盘交互、深色模式下的下拉菜单仍需人工点一遍。
- P4 选择「完整缓存后播放」优先稳定性：首声仍取决于整首下载速度，但等待期间有转圈/百分比；若以后要做低延迟，必须先修好流代理的截断、重试与 Range 结束处理，不能直接暴露 `.part`。
- 在线曲目的 `cover_url` 仍未抓取（当前只接本地内嵌图与 covers 目录），搜索页结果在缓存前一直是首字色块。
- 顶部周杰伦真实封面截图里的封面是脚本为验证链路临时生成的渐变图，不是歌曲自带封面。
