# MingCute Icon Attribution

The `.svg` files in this directory are vendored from the
[MingCute Icon](https://github.com/mingcute-design/mingcute-icons) set,
licensed under the **Apache License 2.0**.

Only the exact 20 icons CS4S actually uses were vendored — this is not a full
copy of the library. Source paths (relative to `mingcute-icons/svg/`):

| CS4S name | Source file |
|---|---|
| `play.svg` | `media/play_line.svg` |
| `stop.svg` | `media/stop_line.svg` |
| `connect.svg` | `device/wifi_line.svg` |
| `disconnect.svg` | `device/wifi_off_line.svg` |
| `upload.svg` | `file/upload_line.svg` |
| `download.svg` | `file/download_line.svg` |
| `refresh.svg` | `system/refresh_1_line.svg` |
| `folder-add.svg` | `file/new_folder_line.svg` |
| `arrow-left.svg` | `arrow/arrow_left_line.svg` |
| `arrow-up.svg` | `arrow/arrow_up_line.svg` |
| `flask.svg` | `education/flask_line.svg` |
| `user-add.svg` | `user/user_add_line.svg` |
| `user-x.svg` | `user/user_remove_line.svg` |
| `trash.svg` | `system/delete_2_line.svg` |
| `edit.svg` | `editor/edit_line.svg` |
| `move.svg` | `arrow/transfer_line.svg` |
| `terminal.svg` | `development/terminal_line.svg` |
| `folder.svg` | `file/folder_line.svg` |
| `leaf.svg` | `nature/leaf_line.svg` |
| `grass.svg` | `nature/grass_line.svg` |

Each file ships with a single fixed fill color (`#09244B`) on its visible path.
`src/ui/icons/icon_provider.py` substitutes that fill at render time so the
same vendored asset renders correctly against both MintPy themes and on
filled accent buttons — see `icon_provider.get_icon()`.

Full license text: https://github.com/mingcute-design/mingcute-icons/blob/main/LICENSE
