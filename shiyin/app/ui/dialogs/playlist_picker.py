"""把歌曲加入自建歌单：下拉选择已有歌单，或就地新建一个。"""

from __future__ import annotations

from PySide6.QtWidgets import QInputDialog

NEW_PLAYLIST = "＋ 新建歌单…"


def choose_playlist(parent, repository) -> str | None:
    """返回选中的歌单 id；用户取消返回 None。"""
    user_lists = [p for p in repository.list_playlists() if p["kind"] == "user"]
    options = [p["name"] for p in user_lists] + [NEW_PLAYLIST]
    choice, ok = QInputDialog.getItem(parent, "加入歌单", "选择目标歌单：", options, 0, False)
    if not ok or not choice:
        return None
    if choice == NEW_PLAYLIST:
        name, ok = QInputDialog.getText(parent, "新建歌单", "歌单名称：")
        if not ok or not name.strip():
            return None
        return repository.create_playlist(name.strip())
    for playlist in user_lists:
        if playlist["name"] == choice:
            return playlist["id"]
    return None


def add_track(parent, repository, track) -> str:
    """执行"加入歌单"，返回可直接显示给用户的提示；取消时返回空串。"""
    playlist_id = choose_playlist(parent, repository)
    if not playlist_id:
        return ""
    repository.add_to_playlist(playlist_id, track)
    return f"已加入歌单：{track.display}"
