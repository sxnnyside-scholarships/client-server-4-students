#!/usr/bin/env python3
"""
Build script for CS4S using PyInstaller.
Produces standalone executables for the current platform.
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    print("Building CS4S Distribution...")

    # Ensure we are in the project root
    project_root = Path(__file__).parent.parent.absolute()
    os.chdir(project_root)

    if not (project_root / "src").exists():
        print("Error: Could not find 'src' directory. Run from project root.")
        sys.exit(1)

    # Locate pyinstaller within the current virtualenv if possible
    python_dir = Path(sys.executable).parent
    pyinstaller_name = "pyinstaller.exe" if os.name == "nt" else "pyinstaller"
    pyinstaller_path = python_dir / pyinstaller_name

    if pyinstaller_path.exists():
        pyinstaller_cmd = str(pyinstaller_path)
    else:
        # Fallback to system-wide executable
        pyinstaller_cmd = "pyinstaller"

    is_macos = sys.platform == "darwin"

    # Build the PyInstaller command
    # We include localization, themes and icons as bundled data assets
    command = [
        pyinstaller_cmd,
        "--noconfirm",
        "--clean",
        "--windowed",  # No console window on launch
        "--name",
        "CS4S",
        "--add-data",
        f"src/localization{os.pathsep}src/localization",
        "--add-data",
        f"src/ui/themes{os.pathsep}src/ui/themes",
        "--add-data",
        f"src/ui/icons{os.pathsep}src/ui/icons",
    ]

    if not is_macos:
        # On macOS, skip --onefile so PyInstaller creates a proper .app bundle
        # (a self-contained directory) instead of a raw Unix binary.
        # On Windows and Linux, a single portable file is the standard.
        command.append("--onefile")

    command.append("main.py")

    print(f"Running command: {' '.join(command)}")

    try:
        subprocess.run(command, check=True)
        print("\nBuild completed successfully!")
        print("Executables can be found in the 'dist/' directory.")
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with exit code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: 'pyinstaller' not found. Ensure it is installed via Poetry.")
        sys.exit(1)


if __name__ == "__main__":
    main()
