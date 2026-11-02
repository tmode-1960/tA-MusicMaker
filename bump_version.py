"""Version manager and bumper for tA-MusicMaker.

Usage:
    python bump_version.py --bump       # Increments by 0.01 (or initializes to 0.50 if not yet set)
    python bump_version.py --set 0.55   # Sets specific version
    python bump_version.py --sync       # Syncs current version across all project files
    python bump_version.py              # Defaults to --bump
"""

from __future__ import annotations

import argparse
from decimal import Decimal
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(BASE_DIR, "version.txt")
SERVER_FILE = os.path.join(BASE_DIR, "server.py")
HTML_FILE = os.path.join(BASE_DIR, "web", "index.html")
ISS_FILE = os.path.join(BASE_DIR, "installer.iss")


def read_version() -> str | None:
    if os.path.isfile(VERSION_FILE):
        with open(VERSION_FILE, "r", encoding="utf-8") as fh:
            v = fh.read().strip()
            if v:
                return v
    return None


def write_version(ver: str) -> None:
    with open(VERSION_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(ver + "\n")


def update_server_py(ver: str) -> None:
    if not os.path.isfile(SERVER_FILE):
        return
    with open(SERVER_FILE, "r", encoding="utf-8") as fh:
        content = fh.read()
    if re.search(r'APP_VERSION\s*=\s*"[^"]*"', content):
        content = re.sub(r'APP_VERSION\s*=\s*"[^"]*"', f'APP_VERSION = "{ver}"', content, count=1)
    else:
        content = f'APP_VERSION = "{ver}"\n' + content
    with open(SERVER_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def update_html(ver: str) -> None:
    if not os.path.isfile(HTML_FILE):
        return
    with open(HTML_FILE, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Update <title>
    content = re.sub(
        r"<title>.*?</title>",
        f"<title>thomo.ART MusicMaker v{ver} (Lantern House Edition)</title>",
        content,
        count=1,
    )

    # Update header brand
    if '<span class="brand-version"' in content:
        content = re.sub(
            r'<span class="brand-version"[^>]*>.*?</span>',
            f'<span class="brand-version" id="brandVersion">v{ver}</span>',
            content,
            count=1,
        )
    else:
        content = content.replace(
            '<b class="brand-title">MusicMaker</b>',
            f'<b class="brand-title">MusicMaker</b> <span class="brand-version" id="brandVersion">v{ver}</span>',
        )

    with open(HTML_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def update_iss(ver: str) -> None:
    if not os.path.isfile(ISS_FILE):
        return
    with open(ISS_FILE, "r", encoding="utf-8") as fh:
        content = fh.read()
    content = re.sub(
        r'#define\s+MyAppVersion\s+"[^"]*"',
        f'#define MyAppVersion "{ver}"',
        content,
        count=1,
    )
    with open(ISS_FILE, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def sync_all(ver: str) -> None:
    write_version(ver)
    update_server_py(ver)
    update_html(ver)
    update_iss(ver)
    print(f"[Version] Synchronisiert auf v{ver}")


def bump_version() -> str:
    cur = read_version()
    if cur is None:
        new_v = "0.50"
    else:
        d = Decimal(cur) + Decimal("0.01")
        new_v = f"{d:.2f}"
    sync_all(new_v)
    return new_v


def main():
    parser = argparse.ArgumentParser(description="tA-MusicMaker Version Manager")
    parser.add_argument("--bump", action="store_true", help="Increment version by 0.01")
    parser.add_argument("--set", type=str, dest="set_ver", help="Set explicit version")
    parser.add_argument("--sync", action="store_true", help="Sync existing version.txt")
    args = parser.parse_args()

    if args.set_ver:
        v = f"{Decimal(args.set_ver):.2f}"
        sync_all(v)
    elif args.sync:
        cur = read_version() or "0.50"
        sync_all(cur)
    else:
        # Default behavior: bump
        bump_version()


if __name__ == "__main__":
    main()
