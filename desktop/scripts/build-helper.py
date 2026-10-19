#!/usr/bin/env python3
"""从仓库现有安全点击助手源码构建 macOS sidecar 资源。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


DESKTOP_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = DESKTOP_ROOT.parent
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts import zombie_common  # noqa: E402


def main() -> int:
    """用 Apple ApplicationServices 编译输入助手，不依赖运行时 Python。"""
    if sys.platform != "darwin":
        print("CGClick helper 只能在 macOS 上构建。", file=sys.stderr)
        return 2
    helper_dir = DESKTOP_ROOT / "src-tauri" / "resources" / "bin"
    build_dir = DESKTOP_ROOT / "build"
    helper_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)
    source = build_dir / "zombie_cgclick.c"
    binary = helper_dir / "zombie_cgclick"
    source.write_text(zombie_common.CGCLICK_SOURCE, encoding="utf-8")
    subprocess.run(
        [
            "clang",
            "-O2",
            "-framework",
            "ApplicationServices",
            str(source),
            "-o",
            str(binary),
        ],
        check=True,
    )
    binary.chmod(binary.stat().st_mode | 0o111)
    print(f"Built {binary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
