"""手绘单色矢量图标。

不引入图片资源或图标字体：打包后不会出现"图标文件没被收集"的问题。
所有图标都按 64×64 画布绘制，交给 Qt 缩放到 16/20/32，不依赖特定字号。
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_CANVAS = 64


def _canvas() -> tuple[QPixmap, QPainter]:
    pixmap = QPixmap(_CANVAS, _CANVAS)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    return pixmap, painter


def _done(pixmap: QPixmap, painter: QPainter) -> QIcon:
    painter.end()
    return QIcon(pixmap)


def heart(color: str = "#4b5563", filled: bool = False) -> QIcon:
    """收藏图标；filled=True 为实心红/绿，用于"已收藏"。"""
    pixmap, painter = _canvas()
    path = QPainterPath()
    path.moveTo(32, 52)
    path.cubicTo(16, 42, 10, 30, 12, 22)
    path.cubicTo(14, 13, 25, 12, 32, 21)
    path.cubicTo(39, 12, 50, 13, 52, 22)
    path.cubicTo(54, 30, 48, 42, 32, 52)
    if filled:
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPath(path)
    else:
        painter.setPen(QPen(QColor(color), 4))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
    return _done(pixmap, painter)


def clock(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(QPen(QColor(color), 4))
    painter.drawEllipse(QRectF(11, 11, 42, 42))
    painter.drawLine(QPointF(32, 32), QPointF(32, 19))
    painter.drawLine(QPointF(32, 32), QPointF(43, 37))
    return _done(pixmap, painter)


def list_icon(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(QPen(QColor(color), 4))
    for y in (18, 32, 46):
        painter.drawLine(QPointF(26, y), QPointF(52, y))
        painter.drawLine(QPointF(14, y), QPointF(18, y))
    return _done(pixmap, painter)


def folder(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(QPen(QColor(color), 4))
    path = QPainterPath()
    path.moveTo(11, 20)
    path.lineTo(26, 20)
    path.lineTo(31, 27)
    path.lineTo(53, 27)
    path.lineTo(53, 49)
    path.lineTo(11, 49)
    path.closeSubpath()
    painter.drawPath(path)
    return _done(pixmap, painter)


def download(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(QPen(QColor(color), 4))
    painter.drawLine(QPointF(32, 12), QPointF(32, 40))
    path = QPainterPath()
    path.moveTo(21, 31)
    path.lineTo(32, 43)
    path.lineTo(43, 31)
    painter.drawPath(path)
    painter.drawLine(QPointF(18, 51), QPointF(46, 51))
    return _done(pixmap, painter)


def note(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(QPen(QColor(color), 4))
    painter.setBrush(QColor(color))
    painter.drawEllipse(QRectF(17, 37, 15, 13))
    painter.drawLine(QPointF(31, 43), QPointF(31, 14))
    path = QPainterPath()
    path.moveTo(31, 16)
    path.cubicTo(38, 17, 44, 20, 46, 27)
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)
    return _done(pixmap, painter)


def gear(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(QPen(QColor(color), 3))
    painter.drawEllipse(QRectF(20, 20, 24, 24))
    painter.setBrush(QColor(color))
    for index in range(8):
        angle = math.radians(index * 45)
        inner = 14
        outer = 21
        dx, dy = math.cos(angle), math.sin(angle)
        painter.drawLine(
            QPointF(32 + dx * inner, 32 + dy * inner),
            QPointF(32 + dx * outer, 32 + dy * outer),
        )
    return _done(pixmap, painter)


def search(color: str = "#8a8f99") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(QPen(QColor(color), 4))
    painter.drawEllipse(QRectF(16, 16, 28, 28))
    painter.drawLine(QPointF(42, 42), QPointF(52, 52))
    return _done(pixmap, painter)


def play(color: str = "#ffffff") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    path = QPainterPath()
    path.moveTo(23, 12)
    path.lineTo(52, 32)
    path.lineTo(23, 52)
    path.closeSubpath()
    painter.drawPath(path)
    return _done(pixmap, painter)


def pause(color: str = "#ffffff") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(QRectF(21, 12, 8, 40), 2, 2)
    painter.drawRoundedRect(QRectF(35, 12, 8, 40), 2, 2)
    return _done(pixmap, painter)


def previous(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    path = QPainterPath()
    path.moveTo(47, 12)
    path.lineTo(21, 32)
    path.lineTo(47, 52)
    path.closeSubpath()
    painter.drawPath(path)
    painter.drawRoundedRect(QRectF(15, 12, 5, 40), 2, 2)
    return _done(pixmap, painter)


def next_icon(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    path = QPainterPath()
    path.moveTo(17, 12)
    path.lineTo(43, 32)
    path.lineTo(17, 52)
    path.closeSubpath()
    painter.drawPath(path)
    painter.drawRoundedRect(QRectF(44, 12, 5, 40), 2, 2)
    return _done(pixmap, painter)


def queue(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(QPen(QColor(color), 4))
    for y in (17, 27, 37, 47):
        painter.drawLine(QPointF(20, y), QPointF(52, y))
        painter.drawLine(QPointF(12, y), QPointF(15, y))
    return _done(pixmap, painter)


def volume(color: str = "#4b5563") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(QPen(QColor(color), 3))
    painter.setBrush(QColor(color))
    path = QPainterPath()
    path.moveTo(10, 26)
    path.lineTo(19, 26)
    path.lineTo(30, 17)
    path.lineTo(30, 47)
    path.lineTo(19, 38)
    path.lineTo(10, 38)
    path.closeSubpath()
    painter.drawPath(path)
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(QRectF(28, 22, 20, 20), -60 * 16, 120 * 16)
    painter.drawArc(QRectF(28, 14, 32, 36), -60 * 16, 120 * 16)
    return _done(pixmap, painter)


def more(color: str = "#6b7280") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(color))
    for x in (18, 32, 46):
        painter.drawEllipse(QPointF(x, 32), 3.5, 3.5)
    return _done(pixmap, painter)


NAV_ICONS = {
    "favorites": heart,
    "recent": clock,
    "queue": list_icon,
    "library": folder,
    "downloads": download,
    "playlists": note,
    "settings": gear,
}


def nav_icon(key: str, color: str = "#4b5563") -> QIcon:
    factory = NAV_ICONS.get(key)
    return factory(color) if factory else QIcon()
