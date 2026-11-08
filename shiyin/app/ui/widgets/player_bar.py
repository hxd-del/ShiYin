"""播放栏：三段式 —— 左曲目信息 / 中控制与进度 / 右队列·音量·歌词。

布局参照 QQ 音乐：白底、左封面+歌名+收藏、中间圆形播放键、右侧入口；
缓冲进度不再铺满整条，改为进度槽底部的细线。
"""

from __future__ import annotations

import time

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy,
                               QVBoxLayout, QWidget)

from shiyin.app.adapters.source_catalog import source_label
from shiyin.app.core.models import Track
from shiyin.app.ui.models.track_model import track_cover_pixmap
from shiyin.app.ui.widgets import icons
from shiyin.app.ui.widgets.buffer_spinner import BufferSpinner
from shiyin.app.ui.widgets.click_slider import ClickSlider


def _fmt(ms: int) -> str:
    seconds = max(0, int(ms) // 1000)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class PlayerBar(QFrame):
    def __init__(self, playback, repository=None, parent=None):
        super().__init__(parent)
        self.playback = playback
        self.repository = repository
        self._dragging = False
        self.setObjectName("playerBar")
        self.setFixedHeight(88)

        # 缓冲动画相关
        self._buffer_percent = 0
        self._target_percent = 0  # 目标百分比
        self._is_buffering = False
        self._buffer_completed = False  # 标记是否已完成缓冲
        self._no_progress_count = 0  # 无进度计数器
        self._last_actual_percent = 0  # 上次获取到的实际进度
        self._loading = True  # 切换歌曲时屏蔽旧信号
        self._buffer_timer = QTimer()
        self._buffer_timer.timeout.connect(self._update_buffer_animation)
        self._buffering_ui_active = False
        self._buffer_display_percent = -1
        self._artist_text = "选一首歌开始"
        self._last_position = -1

        # 某些本地文件/后端组合不会稳定发 durationChanged，或位置信号偶尔
        # 断掉；用一个轻量轮询兜底，保证进度条不会永远停在 00:00。
        self._position_poll = QTimer(self)
        self._position_poll.setInterval(250)
        self._position_poll.timeout.connect(self._poll_position)

        # 音量记忆：拖动时只改后端音量，停手 400ms 再落盘，
        # 避免滑一下写几十次 config.json（Windows 上会撞 WinError 5）。
        self._volume_save_timer = QTimer(self)
        self._volume_save_timer.setSingleShot(True)
        self._volume_save_timer.setInterval(400)
        self._volume_save_timer.timeout.connect(self._persist_volume)
        self._pending_volume = None

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 6, 16, 6)
        root.setSpacing(16)

        # ---------------- 左：曲目信息 ----------------
        info_section = QWidget()
        info_section.setObjectName("barInfo")
        info_section.setFixedWidth(240)
        self.info_section = info_section
        info_row = QHBoxLayout(info_section)
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(10)

        self._icon_color = "#6b7280"

        self.cover = QLabel("♪")
        self.cover.setObjectName("cover")
        self.cover.setFixedSize(56, 56)
        self.cover.setAlignment(Qt.AlignCenter)
        info_row.addWidget(self.cover)

        info = QVBoxLayout()
        info.setSpacing(2)
        info.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("未在播放")
        self.title_label.setObjectName("trackTitle")
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.artist_label = QLabel("选一首歌开始")
        self.artist_label.setObjectName("trackArtist")
        self.artist_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        info.addWidget(self.title_label)
        info.addWidget(self.artist_label)
        info_row.addLayout(info, 1)

        self.fav_btn = QPushButton()
        self.fav_btn.setObjectName("iconButton")
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.setIcon(icons.heart(self._icon_color, filled=False))
        self.fav_btn.setIconSize(QSize(20, 20))
        self.fav_btn.setToolTip("收藏")
        info_row.addWidget(self.fav_btn)

        self.more_btn = QPushButton()
        self.more_btn.setObjectName("iconButton")
        self.more_btn.setFixedSize(28, 28)
        self.more_btn.setIcon(icons.more(self._icon_color))
        self.more_btn.setIconSize(QSize(18, 18))
        self.more_btn.setToolTip("更多")
        info_row.addWidget(self.more_btn)

        root.addWidget(info_section)

        # ---------------- 中：控制 + 进度 ----------------
        center_section = QWidget()
        center_section.setObjectName("barCenter")
        self.center_section = center_section
        center = QVBoxLayout(center_section)
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(2)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addStretch(1)

        self.repeat_btn = QPushButton("顺序")
        self.repeat_btn.setObjectName("ghostButton")
        self.repeat_btn.setFixedHeight(26)
        self.repeat_btn.setToolTip("循环模式")
        buttons.addWidget(self.repeat_btn)

        self.prev_btn = QPushButton()
        self.prev_btn.setObjectName("iconButton")
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setIcon(icons.previous(self._icon_color))
        self.prev_btn.setIconSize(QSize(20, 20))
        self.prev_btn.setToolTip("上一首")
        buttons.addWidget(self.prev_btn)

        self.play_btn = QPushButton()
        self.play_btn.setObjectName("playButton")
        self.play_btn.setFixedSize(44, 44)
        self.play_btn.setIcon(icons.play("#ffffff"))
        self.play_btn.setIconSize(QSize(22, 22))
        self.play_btn.setToolTip("播放")
        buttons.addWidget(self.play_btn)

        # 覆盖在播放键上的缓冲转圈；点击仍然穿透到播放键。
        # 播放键本身是绿底，转圈必须用白色才看得出来。
        self._buffer_spinner = BufferSpinner(self.play_btn, size=44, color="#ffffff")
        self._buffer_spinner.move(0, 0)

        self.next_btn = QPushButton()
        self.next_btn.setObjectName("iconButton")
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setIcon(icons.next_icon(self._icon_color))
        self.next_btn.setIconSize(QSize(20, 20))
        self.next_btn.setToolTip("下一首")
        buttons.addWidget(self.next_btn)

        buttons.addStretch(1)
        center.addLayout(buttons)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        progress_row.setContentsMargins(0, 0, 0, 0)
        self.pos_label = QLabel("00:00")
        self.pos_label.setObjectName("timeLabel")
        self.pos_label.setFixedWidth(42)
        self.pos_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.slider = ClickSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setEnabled(False)  # 时长未知前点了会 seek 到错误位置
        self.dur_label = QLabel("00:00")
        self.dur_label.setObjectName("timeLabel")
        self.dur_label.setFixedWidth(42)
        progress_row.addWidget(self.pos_label)
        progress_row.addWidget(self.slider, 1)
        progress_row.addWidget(self.dur_label)
        center.addLayout(progress_row)

        root.addWidget(center_section, 1)

        # ---------------- 右：队列 / 音量 / 歌词 ----------------
        right_section = QWidget()
        right_section.setObjectName("barRight")
        right_section.setFixedWidth(210)
        self.right_section = right_section
        right_row = QHBoxLayout(right_section)
        right_row.setContentsMargins(0, 0, 0, 0)
        right_row.setSpacing(8)
        right_row.addStretch(1)

        self.queue_btn = QPushButton()
        self.queue_btn.setObjectName("iconButton")
        self.queue_btn.setFixedSize(30, 30)
        self.queue_btn.setIcon(icons.queue(self._icon_color))
        self.queue_btn.setIconSize(QSize(18, 18))
        self.queue_btn.setToolTip("播放列表")
        right_row.addWidget(self.queue_btn)

        volume_icon = QLabel()
        volume_icon.setPixmap(icons.volume(self._icon_color).pixmap(18, 18))
        volume_icon.setFixedSize(18, 18)
        self.volume_icon = volume_icon
        right_row.addWidget(volume_icon)

        self.volume = ClickSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setFixedWidth(84)
        self.volume.setToolTip("音量")
        right_row.addWidget(self.volume)

        self.lyric_btn = QPushButton("词")
        self.lyric_btn.setObjectName("lyricButton")
        self.lyric_btn.setFixedSize(30, 30)
        self.lyric_btn.setToolTip("歌词")
        right_row.addWidget(self.lyric_btn)

        root.addWidget(right_section)

        # 回调（由 MainWindow 设置）
        self._on_lyric_clicked = None
        self._on_queue_clicked = None

        self._wire()

    # ---------------- 绑定 ----------------
    def _wire(self) -> None:
        self.play_btn.clicked.connect(self.playback.toggle)
        self.prev_btn.clicked.connect(self.playback.previous)
        self.next_btn.clicked.connect(self.playback.next)
        self.repeat_btn.clicked.connect(self._cycle_repeat)
        self.slider.sliderPressed.connect(self._on_press)
        self.slider.sliderReleased.connect(self._on_release)
        self.volume.valueChanged.connect(self._on_volume_changed)
        self.fav_btn.clicked.connect(self._toggle_favorite)
        self.more_btn.clicked.connect(self._open_menu)
        self.queue_btn.clicked.connect(self._open_queue)
        self.lyric_btn.clicked.connect(self._open_lyric)

        backend = self.playback.backend
        backend.positionChanged.connect(self._on_position)
        backend.durationChanged.connect(self._on_duration)
        backend.stateChanged.connect(self._on_state)
        self.playback.currentChanged.connect(self._on_track)
        self.playback.failed.connect(self._on_playback_failed)
        self._position_poll.start()

        settings = getattr(self.playback, "settings", None)
        if settings:
            volume = int(float(settings.get("volume") or 0.8) * 100)
            self.volume.blockSignals(True)
            self.volume.setValue(volume)
            self.volume.blockSignals(False)
            self.playback.backend.set_volume(volume / 100)
            self._update_repeat_label(self.playback.repeat)

        self._sync_favorite()

    # ---------------- 入口按钮 ----------------
    def _open_queue(self) -> None:
        if self._on_queue_clicked:
            self._on_queue_clicked()

    def _open_lyric(self) -> None:
        if self._on_lyric_clicked:
            self._on_lyric_clicked()

    def _open_menu(self) -> None:
        track = self.playback.current
        menu = QMenu(self)
        favorite = self._is_favorite(track)
        menu.addAction("取消收藏" if favorite else "收藏", self._toggle_favorite)
        if track:
            menu.addAction("加入歌单…", self._add_to_playlist)
        menu.exec(self.more_btn.mapToGlobal(self.more_btn.rect().bottomLeft()))

    def _add_to_playlist(self) -> None:
        track = self.playback.current
        if not track or not self.repository:
            return
        from shiyin.app.ui.dialogs.playlist_picker import add_track

        add_track(self, self.repository, track)

    def set_theme(self, dark: bool) -> None:
        """切换主题时重绘自绘图标（QSS 管不到 QIcon 颜色）。"""
        self._icon_color = "#b8c0cc" if dark else "#6b7280"
        self.prev_btn.setIcon(icons.previous(self._icon_color))
        self.next_btn.setIcon(icons.next_icon(self._icon_color))
        self.queue_btn.setIcon(icons.queue(self._icon_color))
        self.more_btn.setIcon(icons.more(self._icon_color))
        self.volume_icon.setPixmap(icons.volume(self._icon_color).pixmap(18, 18))
        self._sync_favorite()

    # ---------------- 收藏 ----------------
    def _is_favorite(self, track: Track | None) -> bool:
        if not track or not self.repository:
            return False
        try:
            return self.repository.is_in_playlist("favorites", track.id)
        except Exception:
            return False

    def _sync_favorite(self) -> None:
        active = self._is_favorite(self.playback.current)
        self.fav_btn.setIcon(icons.heart("#2ecb71" if active else self._icon_color, filled=active))
        self.fav_btn.setIconSize(QSize(20, 20))
        self.fav_btn.setToolTip("取消收藏" if active else "收藏")

    def _toggle_favorite(self) -> None:
        track = self.playback.current
        if not track or not self.repository:
            return
        if self._is_favorite(track):
            self.repository.remove_from_playlist("favorites", track.id)
        else:
            self.repository.add_to_playlist("favorites", track)
        self._sync_favorite()

    # ---------------- 缓冲反馈 ----------------
    def _start_buffering_ui(self) -> None:
        """播放键转圈 + 歌手行显示缓存进度，直到真正出声或失败。"""
        self._buffering_ui_active = True
        self._buffer_display_percent = -1
        self._buffer_spinner.start()
        self.artist_label.setText("缓存中…")
        self.artist_label.setToolTip("正在从音源缓存音频，缓存到可播放时会自动开始")

    def _stop_buffering_ui(self) -> None:
        if not self._buffering_ui_active:
            return
        self._buffering_ui_active = False
        self._buffer_spinner.stop()
        self.artist_label.setText(self._artist_text)
        self.artist_label.setToolTip(self._artist_text)

    def _on_playback_failed(self, message: str) -> None:
        self._stop_buffering_ui()
        # 失败原因展示在歌手行，否则“点歌没反应/只播 30s”会让人不知道发生了什么
        self.artist_label.setText(message)
        self.artist_label.setToolTip(message)

    # ---------------- 曲目 ----------------
    def _on_track(self, track: Track) -> None:
        self.title_label.setText(track.title)
        self.title_label.setToolTip(track.title)
        subtitle = " · ".join(part for part in [track.artist, source_label(track.source)] if part)
        self._artist_text = subtitle
        self.artist_label.setText(subtitle)
        self.artist_label.setToolTip(subtitle)
        self.cover.setText("")
        self.cover.setPixmap(track_cover_pixmap(track, 56))
        self._sync_favorite()
        # 标记为加载中，屏蔽旧歌曲的位置/时长信号
        self._loading = True
        self._last_position = -1
        # 重置进度条
        self.slider.setEnabled(False)
        self.slider.setRange(0, 1000)
        self.slider.setValue(0)
        self.pos_label.setText("00:00")
        self.dur_label.setText("00:00")

        # 本地文件时长在库里已经知道，先把它画出来；后端若迟迟不发
        # durationChanged，也不会一直显示 00:00 / 0。
        if track.is_local and track.duration_ms > 0:
            self._apply_duration(track.duration_ms)

        # 本地音乐或缓存已完成的音乐不需要缓存动画
        is_cached_complete = False
        if not track.is_local:
            stream_cache = getattr(self.playback, 'stream_cache', None)
            if stream_cache:
                entry = stream_cache.entry(track.id)
                if entry and entry.done:
                    is_cached_complete = True

        if track.is_local or is_cached_complete:
            self._buffer_percent = 0
            self._target_percent = 0
            self._is_buffering = False
            self._buffer_completed = True  # 标记为已完成，不显示动画
            self._buffer_timer.stop()
            self._no_progress_count = 0
            self._stop_buffering_ui()
        else:
            # 在线音乐：启动平滑缓冲动画 + 播放键转圈
            self._buffer_percent = 0
            self._target_percent = 0
            self._last_actual_percent = 0
            self._is_buffering = True
            self._buffer_completed = False
            self._no_progress_count = 0
            self._download_start_time = time.monotonic()
            self._start_buffering_ui()
            self._buffer_timer.start(30)

        self.update()

    def _on_position(self, position: int) -> None:
        if self._dragging or self._loading:
            return
        self._last_position = position
        self.pos_label.setText(_fmt(position))
        # 防止 slider 范围为 0 时 setValue 导致进度条直接到头
        if self.slider.maximum() > 1:
            self.slider.blockSignals(True)
            self.slider.setValue(int(position))
            self.slider.blockSignals(False)

    def _apply_duration(self, duration: int) -> None:
        """写入时长并解锁进度条；只由 durationChanged 或本地时长兜底调用。"""
        if duration <= 0:
            return
        self._loading = False
        self.slider.setEnabled(True)
        self.dur_label.setText(_fmt(duration))
        self.slider.blockSignals(True)
        self.slider.setRange(0, max(1, duration))
        self.slider.blockSignals(False)

    def _on_duration(self, duration: int) -> None:
        # 后端时长为 0 时，使用 Track 模型中保存的 duration_ms 作为回退
        if duration <= 0:
            track = self.playback.current
            if track and track.duration_ms > 0:
                duration = track.duration_ms
        self._apply_duration(duration)

    def _poll_position(self) -> None:
        """位置信号兜底：本地文件/部分后端可能不持续发 positionChanged。"""
        if self._dragging or not self.playback.current:
            return
        try:
            position = int(self.playback.backend.position())
        except Exception:
            return

        # 后端已经在出声、但 durationChanged 没来：用当前曲目时长解锁。
        if self._loading and position > 0:
            track = self.playback.current
            if track and track.duration_ms > 0:
                self._apply_duration(track.duration_ms)
            elif self.playback.backend.duration() > 0:
                self._apply_duration(self.playback.backend.duration())

        if self._loading:
            return
        if position != self._last_position:
            self._on_position(position)

    def show_restored(self, track: Track | None, position_ms: int) -> None:
        """启动恢复后把播放条画成“暂停在指定位置”，不触发缓存动画。"""
        if track is None:
            return
        self._stop_buffering_ui()
        self._buffer_timer.stop()
        self._is_buffering = False
        self._buffer_completed = True
        if track.duration_ms > 0:
            self._apply_duration(track.duration_ms)
        self._loading = False
        duration = max(1, self.slider.maximum())
        position = max(0, min(int(position_ms), duration))
        self._last_position = position
        self.pos_label.setText(_fmt(position))
        self.slider.setValue(position)
        if self.playback.backend.is_playing():
            self.play_btn.setIcon(icons.pause("#ffffff"))
            self.play_btn.setToolTip("暂停")
        else:
            self.play_btn.setIcon(icons.play("#ffffff"))
            self.play_btn.setToolTip("播放")
        self.update()

    def _on_state(self, state: str) -> None:
        # 只有明确的播放/暂停状态才切换按钮图标。
        # loading / buffering 是媒体状态，不代表播放状态；已出声后 Qt 仍可能发
        # BufferingMedia，若在这里改成播放图标，就会出现“歌在放、按钮却是播放键”。
        if state == "playing":
            self.play_btn.setIcon(icons.pause("#ffffff"))
            self.play_btn.setToolTip("暂停")
        elif state in ("paused", "idle", "failed"):
            self.play_btn.setIcon(icons.play("#ffffff"))
            self.play_btn.setToolTip("播放")
        # 更新缓冲状态
        if state == "playing":
            # 缓存已完成/已出声：立即收转圈并把进度定为 100%，避免停在 99%
            self._is_buffering = False
            self._buffer_percent = 100
            self._target_percent = 100
            self._buffer_completed = True
            self._buffer_timer.stop()
            self._stop_buffering_ui()
            # 不要立即停止定时器，让动画完成
        elif state in ("loading", "buffering"):
            self._is_buffering = True
            track = self.playback.current
            # 本地文件、已缓存完成，或播放器实际已在播放（只是媒体状态短暂 Buffering）
            # 都不显示缓存转圈；否则会出现“歌已经在放、按钮是暂停、转圈不停”的假缓冲。
            if (track and not track.is_local and not self._buffer_completed
                    and not self.playback.backend.is_playing()):
                self._start_buffering_ui()
            if not self._buffer_completed and not self._buffer_timer.isActive():
                self._buffer_timer.start(50)
        elif state in ("idle", "failed"):
            # 停止播放/出错时收起转圈，避免等待被取消后一直转
            self._stop_buffering_ui()

    def _update_buffer_animation(self) -> None:
        """更新缓冲动画：平滑填充，基于时间或实际下载进度"""
        if self._buffer_completed:
            return

        # 获取实际缓存进度
        actual_percent, has_error = self._get_actual_buffer_percent()

        if has_error:
            self._buffer_percent = 0
            self._target_percent = 0
            self._is_buffering = False
            self._buffer_completed = True
            self._buffer_timer.stop()
            self.update()
            return

        if actual_percent is not None:
            # 有实际下载进度，直接使用
            self._target_percent = actual_percent
            self._no_progress_count = 0
        else:
            # 没有实际进度，按时间平滑填充（估计 3 秒内完成）
            self._no_progress_count += 1
            if self._no_progress_count > 500:  # 约 15 秒超时
                self._buffer_percent = 0
                self._target_percent = 0
                self._is_buffering = False
                self._buffer_completed = True
                self._buffer_timer.stop()
                self.update()
                return
            # 时间-based 平滑填充：3 秒内从 0 到 85%
            elapsed = time.monotonic() - getattr(self, '_download_start_time', time.monotonic())
            time_percent = min(85, (elapsed / 3.0) * 85)
            self._target_percent = max(self._target_percent, time_percent)

        # 平滑插值到目标值
        diff = self._target_percent - self._buffer_percent
        if abs(diff) > 0.1:
            factor = 0.3 if abs(diff) > 10 else 0.15
            self._buffer_percent += diff * factor
        else:
            self._buffer_percent = self._target_percent

        if self._buffer_percent >= 99.5:
            self._buffer_percent = 100
            self._buffer_completed = True
            self._buffer_timer.stop()
            self._stop_buffering_ui()

        if self._buffering_ui_active:
            percent = int(max(0, min(99, self._buffer_percent)))
            if percent != self._buffer_display_percent:
                self._buffer_display_percent = percent
                self.artist_label.setText(f"缓存中 {percent}%")

        self.update()

    def _get_actual_buffer_percent(self) -> tuple[float | None, bool]:
        """获取实际缓存进度百分比

        Returns:
            (progress_percent, has_error)
            - progress_percent: 进度百分比，None 表示还未就绪
            - has_error: 是否有错误
        """
        try:
            # 获取当前播放的 track
            track = self.playback.current
            if not track or track.is_local:
                return None, False

            # 获取 stream_cache
            stream_cache = getattr(self.playback, 'stream_cache', None)
            if not stream_cache:
                return None, False

            # 获取当前 track 的缓存 entry
            entry = stream_cache.entry(track.id)
            if not entry:
                # entry 还没创建，不是错误，只是还没就绪
                return None, False

            # 检查是否有错误
            if entry.error:
                return None, True

            # 下载线程已经标记完成：直接按 100% 处理，不再依赖可能不准的
            # Content-Length/估算值，避免显示卡在 99% 或转圈不停。
            if entry.done:
                return 100.0, False

            # 计算进度
            if entry.total > 0:
                percent = (entry.downloaded / entry.total) * 100
                return percent, False
            elif entry.downloaded > 0:
                # 总大小未知，但已下载一些数据
                percent = min(99, (entry.downloaded / (1024 * 1024)) * 10)
                return percent, False
            else:
                # 下载刚开始，还没数据
                return 0, False
        except Exception as e:
            print(f"[缓冲] 获取进度失败：{e}")
            return None, False

    def _clear_buffer_background(self) -> None:
        """清除缓冲背景（仅在切换歌曲时调用）"""
        self._buffer_percent = 0
        self._target_percent = 0
        self._last_actual_percent = 0  # 重置实际进度
        self._buffer_completed = False  # 重置完成标记
        self.update()

    def _on_press(self) -> None:
        self._dragging = True

    def _on_release(self) -> None:
        self._dragging = False
        self.playback.seek(self.slider.value())

    def _on_volume_changed(self, value: int) -> None:
        """拖动/点击音量时立即生效，落盘交给防抖定时器。"""
        self._pending_volume = value
        self.playback.backend.set_volume(value / 100)
        self._volume_save_timer.start()

    def _persist_volume(self) -> None:
        value = self._pending_volume
        if value is None:
            return
        self._pending_volume = None
        self.playback.set_volume(value / 100)

    def _cycle_repeat(self) -> None:
        order = {"off": "all", "all": "one", "one": "off"}
        mode = order.get(self.playback.repeat, "off")
        self.playback.set_repeat(mode)
        self._update_repeat_label(mode)

    def _update_repeat_label(self, mode: str) -> None:
        self.repeat_btn.setText({"off": "顺序", "all": "列表循环", "one": "单曲循环"}.get(mode, "顺序"))

    def mousePressEvent(self, event) -> None:
        """处理鼠标点击事件：点击空白区域弹出歌词"""
        # 检查是否点击在空白区域（非控件区域）
        if self._is_blank_area(event.pos()):
            # 触发歌词页面显示
            if self._on_lyric_clicked:
                self._on_lyric_clicked()
        else:
            # 点击在控件区域，正常处理
            super().mousePressEvent(event)

    def _is_blank_area(self, pos) -> bool:
        """判断是否点击在空白区域"""
        # 遍历所有子控件，检查点击位置是否在某个子控件内
        for child in self.findChildren(QWidget):
            if child.isVisible() and child.geometry().contains(pos):
                return False
        return True
