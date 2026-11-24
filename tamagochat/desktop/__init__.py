"""Tout ce qui dépend du système, avec la même interface sur Windows et sur Mac.

    NAME, UPDATE_TAG, BG, MENU_BUTTONS, SEND_KEYS, DELETE_KEYS, STARTUP_LABEL
    font(size, *style), dpi_scale(root), setup_root(root, on_quit), make_transparent(win),
    make_tool_window(win), keep_on_top(windows), set_dpi_aware(), unsupported_reason()
    list_monitors(), work_area_at(x, y), already_running()
    startup_enabled(), set_startup(enable), migrate_startup()
    can_self_update(), update_download_path(), prepare_update(path), install_update(path),
    restart(), cleanup_update_files()
"""
import sys

if sys.platform == "darwin":
    from .macos import *  # noqa: F401,F403
else:
    from .windows import *  # noqa: F401,F403
