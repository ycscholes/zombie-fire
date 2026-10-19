#!/usr/bin/env python3
"""将已签名的 macOS .app 原子升级到固定的 /Applications 位置。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable


DESKTOP_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "向僵尸开炮日常助手.app"
APP_TARGET = Path("/Applications") / APP_NAME


def verify_signed_app(app: Path) -> None:
    """在复制和替换前后都要求 app 的封装签名通过 strict 验证。"""
    subprocess.run(
        ["/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", str(app)],
        check=True,
    )


def compare_requirements(old_app: Path, new_app: Path) -> None:
    """要求 app、worker 与 helper 的默认 designated requirement 保持一致。"""
    subprocess.run(
        [
            "/bin/bash",
            str(DESKTOP_ROOT / "scripts" / "compare-macos-requirements.sh"),
            str(old_app),
            str(new_app),
        ],
        check=True,
    )


def app_is_running(app: Path) -> bool:
    """检查任意路径的助手或 sidecar 进程，避免覆盖运行中的游戏自动化。"""
    # 匹配可执行文件名而非用户路径，覆盖 release 副本并避免正则转义路径。
    executable_pattern = r"(^|/)(zombie-fire-desktop|zombie-fire-worker[^/]*)([[:space:]]|$)"
    result = subprocess.run(
        ["/usr/bin/pgrep", "-f", executable_pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"无法检查应用运行状态（pgrep 返回 {result.returncode}）。")
    return result.returncode == 0


def copy_signed_app(source: Path, destination: Path) -> None:
    """用 macOS ditto 复制签名包，保留应用包元数据。"""
    subprocess.run(["/usr/bin/ditto", str(source), str(destination)], check=True)


def install_app(
    source: Path,
    target: Path = APP_TARGET,
    *,
    verifier: Callable[[Path], None] | None = None,
    requirement_comparator: Callable[[Path, Path], None] | None = None,
    running_check: Callable[[Path], bool] | None = None,
    app_copier: Callable[[Path, Path], None] | None = None,
) -> Path | None:
    """在 /Applications 同卷暂存，再原子换入；失败时还原旧包。"""
    verifier = verifier or verify_signed_app
    requirement_comparator = requirement_comparator or compare_requirements
    running_check = running_check or app_is_running
    app_copier = app_copier or copy_signed_app
    source = source.resolve()
    if not source.is_dir() or not (source / "Contents").is_dir():
        raise RuntimeError(f"构建产物不是有效 .app：{source}")
    verifier(source)
    if target.is_symlink():
        raise RuntimeError(f"拒绝替换符号链接安装路径：{target}")
    if target.exists() and not target.is_dir():
        raise RuntimeError(f"安装位置不是应用目录：{target}")
    if running_check(target):
        raise RuntimeError(f"应用仍在运行，请先正常退出后再升级：{target}")
    if target.exists():
        requirement_comparator(target, source)

    try:
        stage_root = Path(tempfile.mkdtemp(prefix=".zombie-fire-upgrade-", dir=target.parent))
    except OSError as error:
        raise RuntimeError(
            f"无法在 {target.parent} 创建升级暂存目录；请检查当前用户写入权限。不会自动使用管理员权限。"
        ) from error

    staged_app = stage_root / target.name
    backup: Path | None = None
    installed_new_app = False
    try:
        app_copier(source, staged_app)
        verifier(staged_app)
        requirement_comparator(source, staged_app)
        if running_check(target):
            raise RuntimeError(f"应用在暂存期间启动了，请先正常退出后再升级：{target}")

        if target.exists():
            stamp = time.strftime("%Y%m%d-%H%M%S")
            backup = target.with_name(f"{target.name}.backup-{stamp}")
            suffix = 1
            while backup.exists() or backup.is_symlink():
                backup = target.with_name(f"{target.name}.backup-{stamp}-{suffix}")
                suffix += 1
            os.replace(target, backup)

        os.replace(staged_app, target)
        installed_new_app = True
        verifier(target)
        requirement_comparator(source, target)
    except Exception:
        if installed_new_app and target.exists():
            shutil.rmtree(target)
        if backup is not None and backup.exists() and not target.exists():
            os.replace(backup, target)
        raise
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)

    return backup


def main() -> int:
    """升级 CLI 固定安装路径；构建和签名由 npm run build:app 完成。"""
    if sys.platform != "darwin":
        print("macOS 应用只能在 macOS 上安装。", file=sys.stderr)
        return 2
    if len(sys.argv) == 2 and sys.argv[1] == "--check-running":
        try:
            if app_is_running(APP_TARGET):
                print(f"应用仍在运行，请先正常退出后再升级：{APP_TARGET}", file=sys.stderr)
                return 1
        except RuntimeError as error:
            print(f"无法检查应用运行状态：{error}", file=sys.stderr)
            return 1
        print("当前没有运行中的助手或 worker 进程。")
        return 0
    if len(sys.argv) != 2:
        print("用法：python3 scripts/install-macos.py <已签名.app> | --check-running", file=sys.stderr)
        return 2
    try:
        backup = install_app(Path(sys.argv[1]))
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"升级失败：{error}", file=sys.stderr)
        return 1
    if backup is None:
        print(f"已安装：{APP_TARGET}")
    else:
        print(f"已升级：{APP_TARGET}\n旧应用保存在：{backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
