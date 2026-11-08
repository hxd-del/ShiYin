"""曲目列表控件：两行文本 + 行内封面 + 右侧信息（第二批 P2-2）。"""

from __future__ import annotations

from PySide6.QtCore import QItemSelectionModel, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QAbstractItemView, QFrame, QListView, QStyle, QStyledItemDelegate

from shiyin.app.adapters.source_catalog import source_label
from shiyin.app.ui.models.track_model import track_cover_pixmap

ROW_HEIGHT = 64
COVER_SIZE = 40
SIDE_MARGIN = 16
RIGHT_WIDTH = 200
# 抽屉等窄容器里右侧只留时长，避免把歌名挤成省略号
COMPACT_WIDTH = 520

_dark_mode = False


def set_dark_mode(enabled: bool) -> None:
    """由 MainWindow 在切换主题时调用；delegate 是自绘，必须自己换色。"""
    global _dark_mode
    _dark_mode = bool(enabled)


class TrackListDelegate(QStyledItemDelegate):
    """一行两排：歌名（15）+ 歌手（12 灰）；右侧 时长 · 音质 · 来源。"""

    def sizeHint(self, option, index) -> QSize:
        return QSize(option.rect.width(), ROW_HEIGHT)

    def paint(self, painter: QPainter, option, index) -> None:
        track = index.data(Qt.UserRole)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = option.rect
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)
        if selected or hovered:
            if _dark_mode:
                background = QColor("#1c2a2e") if selected else QColor("#20242b")
            else:
                background = QColor("#eafaf0") if selected else QColor("#f7f8fa")
            painter.setPen(Qt.NoPen)
            painter.setBrush(background)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 8, 8)
        if selected:
            painter.setBrush(QColor("#2ecb71"))
            painter.drawRoundedRect(QRect(rect.left() + 2, rect.top() + 12, 3, rect.height() - 24), 1, 1)

        title = (track.title if track else "") or "—"
        artist = (getattr(track, "artist", "") or "未知歌手") if track else ""
        cover = track_cover_pixmap(track, COVER_SIZE) if track else track_cover_pixmap(None, COVER_SIZE)
        cover_x = rect.left() + SIDE_MARGIN
        cover_y = rect.top() + (rect.height() - COVER_SIZE) // 2
        painter.drawPixmap(cover_x, cover_y, cover)

        compact = rect.width() < COMPACT_WIDTH
        right_width = 48 if compact else RIGHT_WIDTH
        text_x = cover_x + COVER_SIZE + 14
        text_width = max(60, rect.right() - SIDE_MARGIN - right_width - text_x)

        title_font = QFont("Microsoft YaHei UI")
        title_font.setPixelSize(15)
        painter.setFont(title_font)
        painter.setPen(QColor("#f1f3f5" if _dark_mode else "#1f2937"))
        title_metrics = QFontMetrics(title_font)
        title_text = title_metrics.elidedText(title, Qt.ElideRight, text_width)
        painter.drawText(QRect(text_x, rect.top() + 11, text_width, 22),
                         int(Qt.AlignLeft | Qt.AlignVCenter), title_text)

        artist_font = QFont("Microsoft YaHei UI")
        artist_font.setPixelSize(12)
        painter.setFont(artist_font)
        painter.setPen(QColor("#9aa4b2" if _dark_mode else "#8a8f99"))
        artist_metrics = QFontMetrics(artist_font)
        artist_text = artist_metrics.elidedText(artist, Qt.ElideRight, text_width)
        painter.drawText(QRect(text_x, rect.top() + 33, text_width, 18),
                         int(Qt.AlignLeft | Qt.AlignVCenter), artist_text)

        if track:
            if compact:
                info = track.duration_text
            else:
                parts = [track.duration_text, track.quality_text, source_label(track.source)]
                info = " · ".join(part for part in parts if part)
            painter.setPen(QColor("#8b96a5" if _dark_mode else "#9aa0a6"))
            info_text = artist_metrics.elidedText(info, Qt.ElideRight, right_width)
            painter.drawText(QRect(rect.right() - SIDE_MARGIN - right_width, rect.top(),
                                   right_width, rect.height()),
                             int(Qt.AlignRight | Qt.AlignVCenter), info_text)
        painter.restore()


class TrackListView(QListView):
    """基于 QListView 的曲目列表，空列表时在中间显示提示文案。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.empty_text = ""

    def select_row(self, row: int) -> None:
        model = self.model()
        if model is None or not (0 <= row < model.rowCount()):
            return
        index = model.index(row, 0)
        self.setCurrentIndex(index)
        self.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)

    def selected_rows(self) -> list[int]:
        """选中行号：SelectRows 行为下 selectedIndexes 会带出整行各列，这里按首列去重。"""
        if self.selectionModel() is None:
            return []
        rows: list[int] = []
        for index in self.selectionModel().selectedIndexes():
            if index.column() == self.modelColumn() and index.row() not in rows:
                rows.append(index.row())
        return rows

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        model = self.model()
        if model is not None and model.rowCount() > 0:
            return
        if not self.empty_text:
            return
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QColor("#9aa4b2" if _dark_mode else "#9aa0a6"))
        font = QFont("Microsoft YaHei UI")
        font.setPixelSize(13)
        painter.setFont(font)
        painter.drawText(self.viewport().rect().adjusted(24, 0, -24, 0),
                         int(Qt.AlignCenter | Qt.TextWordWrap), self.empty_text)
        painter.end()


def style_track_list(view: TrackListView, empty_text: str = "", multi_select: bool = False) -> None:
    view.setFrameShape(QFrame.NoFrame)
    view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    view.setSelectionMode(QAbstractItemView.ExtendedSelection if multi_select
                          else QAbstractItemView.SingleSelection)
    view.setSelectionBehavior(QAbstractItemView.SelectRows)
    view.setUniformItemSizes(True)
    view.setSpacing(0)
    view.setMouseTracking(True)
    view.viewport().setMouseTracking(True)
    view.setItemDelegate(TrackListDelegate(view))
    view.setIconSize(QSize(COVER_SIZE, COVER_SIZE))
    view.empty_text = empty_text
