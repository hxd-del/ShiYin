"""单实例：第二次启动时激活已有窗口，避免两个进程同时抢数据库和缓存目录。"""

from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "shiyin-single-instance"


class SingleInstance:
    def __init__(self, name: str = SERVER_NAME):
        self.name = name
        self._server: Optional[QLocalServer] = None

    def acquire(self) -> bool:
        """已被其它实例占用返回 False；否则本进程成为主实例。"""
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if socket.waitForConnected(300):
            socket.write(b"activate")
            socket.flush()
            socket.waitForBytesWritten(300)
            socket.disconnectFromServer()
            return False
        QLocalServer.removeServer(self.name)
        self._server = QLocalServer()
        if not self._server.listen(self.name):
            # 端口被占用但连不上：放行，宁可能开也不要打不开
            self._server = None
        return True

    def on_activate(self, callback: Callable[[], None]) -> None:
        if not self._server:
            return

        def _handle():
            while self._server and self._server.hasPendingConnections():
                conn = self._server.nextPendingConnection()
                conn.readAll()
                conn.disconnectFromServer()
                try:
                    callback()
                except Exception:
                    pass

        self._server.newConnection.connect(_handle)
