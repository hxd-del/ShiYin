"""歌词页面：全屏覆盖显示歌词，带高亮和滚动效果。"""

from __future__ import annotations

import re
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPainter
from PySide6.QtWidgets import (QFrame, QLabel, QVBoxLayout, QWidget, QPushButton, 
                               QHBoxLayout, QScrollArea)


class LyricLine:
    """单行歌词"""
    def __init__(self, time_ms: int, text: str):
        self.time_ms = time_ms  # 时间戳（毫秒）
        self.text = text  # 歌词文本


class LyricPage(QFrame):
    """歌词页面：全屏覆盖，歌词逐行高亮"""
    
    def __init__(self, playback, parent=None):
        super().__init__(parent)
        self.playback = playback
        self.setObjectName("lyricPage")
        
        # 歌词数据
        self._lyric_lines: list[LyricLine] = []
        self._current_line_index = -1
        
        # 初始状态：隐藏
        self.setVisible(False)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部栏（关闭按钮）
        top_bar = QWidget()
        top_bar.setFixedHeight(60)
        top_bar.setObjectName("lyricTopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 10, 20, 10)
        top_layout.addStretch(1)
        
        # 关闭按钮
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("lyricCloseBtn")
        self.close_btn.setFixedSize(40, 40)
        self.close_btn.clicked.connect(self.hide_lyric)
        top_layout.addWidget(self.close_btn)
        
        layout.addWidget(top_bar)
        
        # 歌曲标题
        self.title_label = QLabel("歌词")
        self.title_label.setObjectName("lyricTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)
        
        # 歌词滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("lyricScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 歌词内容容器
        self.lyric_container = QWidget()
        self.lyric_container.setObjectName("lyricContainer")
        self.lyric_layout = QVBoxLayout(self.lyric_container)
        self.lyric_layout.setContentsMargins(40, 20, 40, 20)
        self.lyric_layout.setSpacing(12)
        self.lyric_layout.addStretch(1)  # 顶部留白
        
        self.scroll_area.setWidget(self.lyric_container)
        layout.addWidget(self.scroll_area, 1)
        
        # 样式
        self.setStyleSheet("""
            QFrame#lyricPage {
                background-color: rgba(20, 20, 30, 230);
            }
            QWidget#lyricTopBar {
                background: transparent;
            }
            QPushButton#lyricCloseBtn {
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 20px;
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton#lyricCloseBtn:hover {
                background-color: rgba(255, 255, 255, 40);
            }
            QLabel#lyricTitle {
                color: #0f9d90;
                font-size: 28px;
                font-weight: bold;
                padding: 20px;
                background: transparent;
            }
            QScrollArea#lyricScrollArea {
                background: transparent;
                border: none;
            }
            QWidget#lyricContainer {
                background: transparent;
            }
        """)
        
        # 绑定信号
        self.playback.currentChanged.connect(self._on_track_changed)
        
        # 定时器：更新歌词高亮
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_lyric_highlight)
        self._update_timer.start(100)  # 每 100ms 更新一次
        
        # 后端信号
        backend = self.playback.backend
        backend.positionChanged.connect(self._on_position_changed)
    
    def _on_track_changed(self, track) -> None:
        """切换歌曲时更新歌词"""
        self._lyric_lines.clear()
        self._current_line_index = -1
        
        # 清空歌词容器
        self._clear_lyric_widgets()
        
        if track and track.lyric:
            self.title_label.setText(f"{track.title} - {track.artist}")
            self._parse_lyric(track.lyric)
            self._create_lyric_widgets()
        else:
            self.title_label.setText("歌词")
            # 显示暂无歌词
            no_lyric_label = QLabel("暂无歌词")
            no_lyric_label.setObjectName("noLyricLabel")
            no_lyric_label.setAlignment(Qt.AlignCenter)
            no_lyric_label.setStyleSheet("""
                QLabel#noLyricLabel {
                    color: rgba(255, 255, 255, 100);
                    font-size: 20px;
                    padding: 100px;
                }
            """)
            self.lyric_layout.addWidget(no_lyric_label)
            self.lyric_layout.addStretch(1)
    
    def _clear_lyric_widgets(self) -> None:
        """清空歌词容器中的所有控件"""
        while self.lyric_layout.count() > 1:  # 保留最后的 stretch
            item = self.lyric_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _parse_lyric(self, lyric: str) -> None:
        """解析歌词文本为 LyricLine 列表"""
        # 匹配时间戳格式：[mm:ss.xx] 或 [mm:ss.xxx] 或 [mm:ss]
        pattern = r'\[(\d{2}):(\d{2})(?:\.(\d{2,3}))?\](.*)'
        
        print(f"[歌词] 开始解析，共 {len(lyric.split(chr(10)))} 行")
        
        for line in lyric.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                ms_str = match.group(3) if match.group(3) else '0'
                milliseconds = int(ms_str.ljust(3, '0'))  # 补齐 3 位
                text = match.group(4).strip()
                
                time_ms = minutes * 60000 + seconds * 1000 + milliseconds
                if text:  # 只添加有文本的行
                    self._lyric_lines.append(LyricLine(time_ms, text))
        
        # 按时间排序
        self._lyric_lines.sort(key=lambda x: x.time_ms)
        print(f"[歌词] 解析完成，共 {len(self._lyric_lines)} 行有效歌词")
    
    def _create_lyric_widgets(self) -> None:
        """创建歌词行控件"""
        for i, line in enumerate(self._lyric_lines):
            label = QLabel(line.text)
            label.setObjectName(f"lyricLine_{i}")
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            label.setProperty("line_index", i)
            label.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 100);
                    font-size: 20px;
                    padding: 12px 20px;
                    background: transparent;
                }
            """)
            self.lyric_layout.addWidget(label)
        
        self.lyric_layout.addStretch(1)  # 底部留白
    
    def _on_position_changed(self, position: int) -> None:
        """播放位置变化时更新歌词高亮"""
        if not self.isVisible():
            return
        self._update_lyric_highlight()
    
    def _update_lyric_highlight(self) -> None:
        """更新歌词高亮"""
        if not self._lyric_lines or not self.isVisible():
            return
        
        # 获取当前播放位置
        try:
            backend = self.playback.backend
            # 直接调用 position() 方法获取位置（返回毫秒）
            position_ms = backend.position() if callable(getattr(backend, 'position', None)) else 0
        except Exception:
            position_ms = 0
        
        # 调试输出
        if position_ms > 0 and position_ms % 1000 < 100:  # 每秒输出一次
            print(f"[歌词] 当前位置：{position_ms}ms, 当前行索引：{self._current_line_index}")
        
        # 找到当前应该高亮的行
        new_index = -1
        for i, line in enumerate(self._lyric_lines):
            if position_ms >= line.time_ms:
                new_index = i
            else:
                break
        
        # 如果行索引变化，更新样式
        if new_index != self._current_line_index:
            print(f"[歌词] 高亮行变化：{self._current_line_index} -> {new_index}")
            self._current_line_index = new_index
            self._refresh_lyric_styles()
            
            # 滚动到当前行
            if new_index >= 0:
                self._scroll_to_line(new_index)
    
    def _refresh_lyric_styles(self) -> None:
        """刷新所有歌词行的样式"""
        for i in range(len(self._lyric_lines)):
            label = self.lyric_container.findChild(QLabel, f"lyricLine_{i}")
            if label:
                if i == self._current_line_index:
                    # 当前行：高亮
                    label.setStyleSheet("""
                        QLabel {
                            color: #0f9d90;
                            font-size: 24px;
                            font-weight: bold;
                            padding: 16px 20px;
                            background: transparent;
                        }
                    """)
                elif i < self._current_line_index:
                    # 已唱过的行：半透明
                    label.setStyleSheet("""
                        QLabel {
                            color: rgba(255, 255, 255, 150);
                            font-size: 20px;
                            padding: 12px 20px;
                            background: transparent;
                        }
                    """)
                else:
                    # 未唱到的行：更淡
                    label.setStyleSheet("""
                        QLabel {
                            color: rgba(255, 255, 255, 80);
                            font-size: 20px;
                            padding: 12px 20px;
                            background: transparent;
                        }
                    """)
    
    def _scroll_to_line(self, line_index: int) -> None:
        """滚动到指定行"""
        label = self.lyric_container.findChild(QLabel, f"lyricLine_{line_index}")
        if label:
            # 计算目标位置（居中显示）
            scroll_area_height = self.scroll_area.height()
            label_y = label.y()
            label_height = label.height()
            target_y = label_y - (scroll_area_height // 2) + (label_height // 2)
            
            # 平滑滚动
            scrollbar = self.scroll_area.verticalScrollBar()
            current_value = scrollbar.value()
            target_value = max(0, min(target_y, scrollbar.maximum()))
            
            # 使用动画平滑滚动（更长的时间和更好的缓动曲线）
            if abs(current_value - target_value) > 10:
                # 停止之前的动画
                if hasattr(self, '_scroll_animation') and self._scroll_animation:
                    self._scroll_animation.stop()
                
                animation = QPropertyAnimation(scrollbar, b"value")
                animation.setDuration(500)  # 更长的动画时间（500ms）
                animation.setStartValue(current_value)
                animation.setEndValue(target_value)
                animation.setEasingCurve(QEasingCurve.InOutCubic)  # 更平滑的缓动曲线
                animation.start()
                # 保存动画引用防止被垃圾回收
                self._scroll_animation = animation
    
    def show_lyric(self) -> None:
        """显示歌词页面"""
        self.setVisible(True)
        self.raise_()
        
        # 更新歌词内容
        track = self.playback.current
        if track:
            self._on_track_changed(track)
        
        # 重置滚动位置到顶部
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(0)
        
        # 等待布局完成后再更新高亮
        QTimer.singleShot(100, self._update_lyric_highlight)
        print(f"[歌词] 页面显示，重置滚动位置并延迟更新高亮")
    
    def hide_lyric(self) -> None:
        """隐藏歌词页面"""
        self.setVisible(False)
