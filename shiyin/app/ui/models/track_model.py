"""列表模型：搜索、库、歌单共用一套只读模型。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPixmap

from shiyin.app.adapters.source_catalog import source_label
from shiyin.app.core.models import Track

HEADERS = ["标题", "歌手", "专辑", "时长", "音质", "来源"]

# 行首封面色块：没有真实封面时用歌名首字，颜色按标题稳定取一色
_COVER_COLORS = ["#2ecb71", "#5b8def", "#f2a33c", "#9b6bd6", "#e86a6a", "#2fb3c4"]
_cover_cache: dict[tuple[str, str, int], QPixmap] = {}
_covers_dir: Path | None = None
_art_cache: dict[tuple[str, int], QPixmap] = {}
# 本地文件没有内嵌封面时不要每次重绘都重新读一遍标签
_missing_art: set[str] = set()


def set_covers_dir(path: str | Path | None) -> None:
    """配置封面落盘目录（由 MainWindow 在构造界面时注入）。"""
    global _covers_dir
    _covers_dir = Path(path) if path else None
    if _covers_dir:
        try:
            _covers_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    _art_cache.clear()
    _missing_art.clear()


def clear_cover_cache() -> None:
    _cover_cache.clear()
    _art_cache.clear()
    _missing_art.clear()


def _cover_key(track) -> str:
    """本地曲目 id 带 ``local:`` 前缀，不能直接当文件名。"""
    raw = getattr(track, "id", "") or getattr(track, "title", "")
    return hashlib.sha1(str(raw).encode("utf-8")).hexdigest()[:16]


def _embedded_art(path: str) -> bytes | None:
    """从本地音频里读内嵌封面：MP3(APIC) / FLAC(picture) / MP4(covr) / Ogg。"""
    try:
        import base64

        import mutagen
        from mutagen.flac import Picture

        audio = mutagen.File(path)
        if audio is None:
            return None
        pictures = getattr(audio, "pictures", None)
        if pictures:
            return bytes(pictures[0].data)
        tags = getattr(audio, "tags", None)
        if tags is None:
            return None
        if hasattr(tags, "getall"):
            apics = tags.getall("APIC")
            if apics:
                return bytes(apics[0].data)
        try:
            covr = tags.get("covr")
            if covr:
                return bytes(covr[0])
        except Exception:
            pass
        try:
            raw = tags.get("metadata_block_picture")
            if raw:
                return bytes(Picture(base64.b64decode(raw[0])).data)
        except Exception:
            pass
    except Exception:
        return None
    return None


def _cover_bytes(track) -> bytes | None:
    """先找缓存文件，再从本地音频抽内嵌封面；抽到就落盘复用。"""
    key = _cover_key(track)
    if _covers_dir:
        for path in _covers_dir.glob(f"cover_{key}.*"):
            try:
                return path.read_bytes()
            except OSError:
                continue
    local = getattr(track, "path", "")
    if not local or not Path(local).exists():
        return None
    data = _embedded_art(local)
    if data and _covers_dir:
        try:
            (_covers_dir / f"cover_{key}.jpg").write_bytes(data)
        except OSError:
            pass
    return data


def _rounded_cover(source: QPixmap, size: int, radius: int = 8) -> QPixmap:
    scaled = source.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    if scaled.width() > size or scaled.height() > size:
        x = max(0, (scaled.width() - size) // 2)
        y = max(0, (scaled.height() - size) // 2)
        scaled = scaled.copy(x, y, size, size)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(scaled))
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.end()
    return pixmap


def track_cover_pixmap(track, size: int = 40) -> QPixmap:
    """真实封面优先（covers 目录 / 内嵌 art），没有才退回首字色块。"""
    if track is None:
        return cover_pixmap("♪", size)
    key = (_cover_key(track), size)
    cached = _art_cache.get(key)
    if cached is not None:
        return cached
    if _cover_key(track) in _missing_art:
        return cover_pixmap(getattr(track, "title", "") or "♪", size)
    data = _cover_bytes(track)
    if not data:
        _missing_art.add(_cover_key(track))
        return cover_pixmap(getattr(track, "title", "") or "♪", size)
    image = QImage.fromData(data)
    if image.isNull():
        _missing_art.add(_cover_key(track))
        return cover_pixmap(getattr(track, "title", "") or "♪", size)
    pixmap = _rounded_cover(QPixmap.fromImage(image), size)
    _art_cache[key] = pixmap
    return pixmap



def cover_pixmap(title: str, size: int = 40) -> QPixmap:
    """生成 40×40 圆角色块 + 首字；结果按（首字, 颜色, 尺寸）缓存。"""
    text = title or "♪"
    char = text[:1].upper()
    color = _COVER_COLORS[sum(ord(ch) for ch in text) % len(_COVER_COLORS)]
    key = (char, color, size)
    cached = _cover_cache.get(key)
    if cached is not None:
        return cached

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(0, 0, size, size, 8, 8)
    font = QFont("Microsoft YaHei UI")
    font.setPixelSize(max(14, size * 0.42))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignCenter, char)
    painter.end()
    _cover_cache[key] = pixmap
    return pixmap


class TrackTableModel(QAbstractTableModel):
    def __init__(self, tracks: list[Track] | None = None, parent=None):
        super().__init__(parent)
        self._tracks: list[Track] = list(tracks or [])

    def set_tracks(self, tracks: list[Track]) -> None:
        self.beginResetModel()
        self._tracks = list(tracks)
        self.endResetModel()

    def track(self, row: int) -> Track | None:
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._tracks)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        track = self._tracks[index.row()]
        column = index.column()
        if role == Qt.DisplayRole:
            return [
                track.title,
                track.artist or "--",
                track.album or "--",
                track.duration_text,
                track.quality_text,
                source_label(track.source),
            ][column]
        if role == Qt.DecorationRole and column == 0:
            return track_cover_pixmap(track)
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignLeft | Qt.AlignVCenter) if column in (0, 1, 2) else int(Qt.AlignCenter)
        if role == Qt.UserRole:
            return track
        if role == Qt.ToolTipRole:
            return f"{track.display}\n{track.source} · {track.ext_clean.upper()} · {track.size_text}"
        return None
