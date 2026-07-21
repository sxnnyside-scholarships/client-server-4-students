import ast
from pathlib import Path


def test_all_referenced_icons_exist():
    ui_dir = Path("src/ui")
    icons_dir = Path("src/ui/icons/mingcute")

    missing = set()
    found = set()

    for py_file in ui_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ("get_icon", "MintIconButton"):
                    if node.args and getattr(node.args[0], "value", None):
                        icon_name = node.args[0].value
                        if isinstance(icon_name, str):
                            if not (icons_dir / f"{icon_name}.svg").exists():
                                missing.add((icon_name, py_file.name))
                            else:
                                found.add(icon_name)
                elif func_name == "add_mode":
                    if len(node.args) >= 2 and getattr(node.args[1], "value", None):
                        icon_name = node.args[1].value
                        if isinstance(icon_name, str):
                            if not (icons_dir / f"{icon_name}.svg").exists():
                                missing.add((icon_name, py_file.name))
                            else:
                                found.add(icon_name)
                elif func_name == "EmptyStateWidget":
                    icon_name = None
                    if len(node.args) >= 3 and getattr(node.args[2], "value", None):
                        if isinstance(node.args[2].value, str):
                            icon_name = node.args[2].value
                    for kw in node.keywords:
                        if kw.arg == "icon_name" and getattr(kw.value, "value", None):
                            if isinstance(kw.value.value, str):
                                icon_name = kw.value.value
                    if icon_name:
                        if not (icons_dir / f"{icon_name}.svg").exists():
                            missing.add((icon_name, py_file.name))
                        else:
                            found.add(icon_name)
                elif func_name == "_make_mode_card":
                    if len(node.args) >= 1 and getattr(node.args[0], "value", None):
                        icon_name = node.args[0].value
                        if isinstance(icon_name, str):
                            if not (icons_dir / f"{icon_name}.svg").exists():
                                missing.add((icon_name, py_file.name))
                            else:
                                found.add(icon_name)

    assert not missing, f"Found references to non-existent icons: {missing}"
