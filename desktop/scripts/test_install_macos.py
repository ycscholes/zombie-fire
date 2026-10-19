"""验证 macOS 安装步骤的运行保护、DR 阻断和回滚行为。"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_PATH = Path(__file__).with_name("install-macos.py")
SPEC = importlib.util.spec_from_file_location("install_macos", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
install_macos = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install_macos)


class MacOSInstallTests(unittest.TestCase):
    def make_app(self, path: Path, marker: str) -> Path:
        """建立带 Contents 的最小测试包，避免调用真实构建或 codesign。"""
        (path / "Contents").mkdir(parents=True)
        (path / "Contents" / "marker.txt").write_text(marker, encoding="utf-8")
        return path

    def test_success_keeps_complete_backup_and_atomically_replaces_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.make_app(root / "release.app", "new build")
            target = self.make_app(root / install_macos.APP_NAME, "old install")
            with (
                mock.patch.object(install_macos, "verify_signed_app") as verify,
                mock.patch.object(install_macos, "compare_requirements") as compare,
            ):
                backup = install_macos.install_app(
                    source,
                    target,
                    running_check=lambda _path: False,
                    app_copier=lambda old, new: shutil.copytree(old, new),
                )

            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertEqual((target / "Contents" / "marker.txt").read_text(), "new build")
            self.assertEqual((backup / "Contents" / "marker.txt").read_text(), "old install")
            self.assertEqual(verify.call_count, 3)
            self.assertEqual(compare.call_count, 3)

    def test_running_app_from_any_copy_blocks_install_without_touching_old_app(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.make_app(root / "release.app", "new build")
            target = self.make_app(root / install_macos.APP_NAME, "old install")
            with mock.patch.object(install_macos, "verify_signed_app"):
                with self.assertRaisesRegex(RuntimeError, "仍在运行"):
                    install_macos.install_app(
                        source,
                        target,
                        running_check=lambda _path: True,
                    )
            self.assertEqual((target / "Contents" / "marker.txt").read_text(), "old install")
            self.assertEqual(list(root.glob("*.backup-*")), [])

    def test_run_check_uses_executable_names_not_an_unescaped_install_path(self) -> None:
        completed = subprocess.CompletedProcess(args=[], returncode=0)
        with mock.patch.object(install_macos.subprocess, "run", return_value=completed) as run:
            self.assertTrue(install_macos.app_is_running(Path("/Applications/向僵尸开炮日常助手.app")))
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["/usr/bin/pgrep", "-f"])
        self.assertIn("zombie-fire-desktop", command[2])
        self.assertIn("zombie-fire-worker", command[2])
        self.assertNotIn("/Applications", command[2])

    def test_changed_existing_requirement_blocks_replacement_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.make_app(root / "release.app", "new build")
            target = self.make_app(root / install_macos.APP_NAME, "old install")
            copier = mock.Mock()
            with mock.patch.object(install_macos, "verify_signed_app"):
                with self.assertRaisesRegex(RuntimeError, "DR changed"):
                    install_macos.install_app(
                        source,
                        target,
                        requirement_comparator=mock.Mock(side_effect=RuntimeError("DR changed")),
                        running_check=lambda _path: False,
                        app_copier=copier,
                    )
            copier.assert_not_called()
            self.assertEqual((target / "Contents" / "marker.txt").read_text(), "old install")

    def test_post_swap_verification_failure_restores_old_app(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.make_app(root / "release.app", "new build")
            target = self.make_app(root / install_macos.APP_NAME, "old install")
            verifier = mock.Mock(side_effect=[None, None, RuntimeError("strict verify failed")])
            with self.assertRaisesRegex(RuntimeError, "strict verify failed"):
                install_macos.install_app(
                    source,
                    target,
                    verifier=verifier,
                    requirement_comparator=lambda _old, _new: None,
                    running_check=lambda _path: False,
                    app_copier=lambda old, new: shutil.copytree(old, new),
                )
            self.assertEqual((target / "Contents" / "marker.txt").read_text(), "old install")
            self.assertEqual(list(root.glob("*.backup-*")), [])

    def test_no_admin_fallback_when_applications_stage_is_not_writable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.make_app(root / "release.app", "new build")
            target = self.make_app(root / install_macos.APP_NAME, "old install")
            with (
                mock.patch.object(install_macos, "verify_signed_app"),
                mock.patch.object(install_macos, "compare_requirements"),
                mock.patch.object(install_macos.tempfile, "mkdtemp", side_effect=PermissionError("denied")),
            ):
                with self.assertRaisesRegex(RuntimeError, "不会自动使用管理员权限"):
                    install_macos.install_app(source, target, running_check=lambda _path: False)
            self.assertEqual((target / "Contents" / "marker.txt").read_text(), "old install")

    def test_symlink_install_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self.make_app(root / "release.app", "new build")
            real_target = self.make_app(root / "real.app", "old install")
            target = root / install_macos.APP_NAME
            target.symlink_to(real_target, target_is_directory=True)
            with mock.patch.object(install_macos, "verify_signed_app"):
                with self.assertRaisesRegex(RuntimeError, "符号链接"):
                    install_macos.install_app(source, target, running_check=lambda _path: False)
            self.assertEqual((real_target / "Contents" / "marker.txt").read_text(), "old install")


if __name__ == "__main__":
    unittest.main()
