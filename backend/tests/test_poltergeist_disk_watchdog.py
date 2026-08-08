import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend.ops.disk_watchdog import inspect_and_prune_disk


def disk_usage(percent):
    total = 100
    used = percent
    return SimpleNamespace(total=total, used=used, free=total - used)


class PoltergeistDiskWatchdogTests(unittest.IsolatedAsyncioTestCase):
    async def test_healthy_disk_clears_degraded_state_without_pruning(self):
        with (
            patch.dict(os.environ, {"SENTINEL_DISK_PATH": "/data"}, clear=True),
            patch("backend.ops.disk_watchdog.os.path.exists", return_value=True),
            patch(
                "backend.ops.disk_watchdog.shutil.disk_usage",
                return_value=disk_usage(42),
            ),
            patch("backend.ops.disk_watchdog.asyncio.to_thread") as to_thread,
        ):
            is_degraded = await inspect_and_prune_disk(90)

        self.assertFalse(is_degraded)
        to_thread.assert_not_called()

    async def test_inaccessible_disk_path_is_degraded(self):
        with (
            patch.dict(os.environ, {"SENTINEL_DISK_PATH": "/missing"}, clear=True),
            patch("backend.ops.disk_watchdog.os.path.exists", return_value=False),
            self.assertLogs("poltergeist_daemon", level="ERROR") as logs,
        ):
            is_degraded = await inspect_and_prune_disk(90)

        self.assertTrue(is_degraded)
        self.assertIn("disk health cannot be verified", "\n".join(logs.output))

    async def test_high_disk_does_not_prune_without_explicit_opt_in(self):
        with (
            patch.dict(os.environ, {"SENTINEL_DISK_PATH": "/data"}, clear=True),
            patch("backend.ops.disk_watchdog.os.path.exists", return_value=True),
            patch(
                "backend.ops.disk_watchdog.shutil.disk_usage",
                return_value=disk_usage(91),
            ),
            patch("backend.ops.disk_watchdog.asyncio.to_thread") as to_thread,
            self.assertLogs("poltergeist_daemon", level="WARNING") as logs,
        ):
            is_degraded = await inspect_and_prune_disk(90)

        self.assertTrue(is_degraded)
        to_thread.assert_not_called()
        self.assertIn("automatic Docker pruning is disabled", "\n".join(logs.output))

    async def test_enabled_prune_requires_a_docker_daemon_endpoint(self):
        env = {
            "SENTINEL_DISK_PATH": "/data",
            "SENTINEL_DOCKER_PRUNE_ENABLED": "true",
        }

        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "backend.ops.disk_watchdog.os.path.exists",
                side_effect=lambda path: path == "/data",
            ),
            patch(
                "backend.ops.disk_watchdog.shutil.disk_usage",
                return_value=disk_usage(91),
            ),
            patch(
                "backend.ops.disk_watchdog.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch("backend.ops.disk_watchdog.asyncio.to_thread") as to_thread,
            self.assertLogs("poltergeist_daemon", level="ERROR") as logs,
        ):
            is_degraded = await inspect_and_prune_disk(90)

        self.assertTrue(is_degraded)
        to_thread.assert_not_called()
        self.assertIn("no Docker daemon endpoint", "\n".join(logs.output))

    async def test_enabled_prune_requires_the_docker_cli(self):
        env = {
            "SENTINEL_DISK_PATH": "/data",
            "SENTINEL_DOCKER_PRUNE_ENABLED": "true",
        }

        with (
            patch.dict(os.environ, env, clear=True),
            patch("backend.ops.disk_watchdog.os.path.exists", return_value=True),
            patch(
                "backend.ops.disk_watchdog.shutil.disk_usage",
                return_value=disk_usage(91),
            ),
            patch("backend.ops.disk_watchdog.shutil.which", return_value=None),
            patch("backend.ops.disk_watchdog.asyncio.to_thread") as to_thread,
            self.assertLogs("poltergeist_daemon", level="ERROR") as logs,
        ):
            is_degraded = await inspect_and_prune_disk(90)

        self.assertTrue(is_degraded)
        to_thread.assert_not_called()
        self.assertIn("docker CLI is unavailable", "\n".join(logs.output))

    async def test_failed_prune_stays_degraded_and_reports_exit_code(self):
        env = {
            "DOCKER_HOST": "unix:///approved/docker.sock",
            "SENTINEL_DISK_PATH": "/data",
            "SENTINEL_DOCKER_PRUNE_ENABLED": "true",
        }
        result = SimpleNamespace(returncode=1, stderr="permission denied", stdout="")

        with (
            patch.dict(os.environ, env, clear=True),
            patch("backend.ops.disk_watchdog.os.path.exists", return_value=True),
            patch(
                "backend.ops.disk_watchdog.shutil.disk_usage",
                return_value=disk_usage(91),
            ),
            patch(
                "backend.ops.disk_watchdog.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch(
                "backend.ops.disk_watchdog.asyncio.to_thread",
                new=AsyncMock(return_value=result),
            ),
            self.assertLogs("poltergeist_daemon", level="ERROR") as logs,
        ):
            is_degraded = await inspect_and_prune_disk(90)

        self.assertTrue(is_degraded)
        self.assertIn("exit code 1", "\n".join(logs.output))
        self.assertIn("permission denied", "\n".join(logs.output))

    async def test_successful_prune_rechecks_disk_before_clearing_degraded_state(self):
        env = {
            "DOCKER_HOST": "unix:///approved/docker.sock",
            "SENTINEL_DISK_PATH": "/data",
            "SENTINEL_DOCKER_PRUNE_ENABLED": "true",
        }
        result = SimpleNamespace(returncode=0, stderr="", stdout="reclaimed space")

        with (
            patch.dict(os.environ, env, clear=True),
            patch("backend.ops.disk_watchdog.os.path.exists", return_value=True),
            patch(
                "backend.ops.disk_watchdog.shutil.disk_usage",
                side_effect=[disk_usage(91), disk_usage(65)],
            ),
            patch(
                "backend.ops.disk_watchdog.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch(
                "backend.ops.disk_watchdog.asyncio.to_thread",
                new=AsyncMock(return_value=result),
            ),
        ):
            is_degraded = await inspect_and_prune_disk(90)

        self.assertFalse(is_degraded)

    async def test_successful_prune_stays_degraded_when_disk_is_still_high(self):
        env = {
            "DOCKER_HOST": "unix:///approved/docker.sock",
            "SENTINEL_DISK_PATH": "/data",
            "SENTINEL_DOCKER_PRUNE_ENABLED": "true",
        }
        result = SimpleNamespace(returncode=0, stderr="", stdout="reclaimed space")

        with (
            patch.dict(os.environ, env, clear=True),
            patch("backend.ops.disk_watchdog.os.path.exists", return_value=True),
            patch(
                "backend.ops.disk_watchdog.shutil.disk_usage",
                side_effect=[disk_usage(94), disk_usage(91)],
            ),
            patch(
                "backend.ops.disk_watchdog.shutil.which",
                return_value="/usr/bin/docker",
            ),
            patch(
                "backend.ops.disk_watchdog.asyncio.to_thread",
                new=AsyncMock(return_value=result),
            ),
        ):
            is_degraded = await inspect_and_prune_disk(90)

        self.assertTrue(is_degraded)
