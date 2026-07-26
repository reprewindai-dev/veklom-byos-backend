"""Disk pressure detection and explicitly enabled Docker cleanup."""

import asyncio
import logging
import os
import shutil
import subprocess

logger = logging.getLogger("poltergeist_daemon")


async def inspect_and_prune_disk(threshold_percent: int) -> bool:
    """Return whether disk health remains degraded after an optional cleanup."""
    try:
        target_path = os.environ.get("SENTINEL_DISK_PATH", "/")
        if not os.path.exists(target_path):
            logger.error(
                f"[sentinel][disk] path {target_path} is not accessible; "
                "disk health cannot be verified"
            )
            return True

        usage = shutil.disk_usage(target_path)
        percent = (usage.used / usage.total) * 100
        if percent < threshold_percent:
            return False

        logger.warning(f"[sentinel][disk] disk at {percent:.1f}%")

        prune_enabled = os.environ.get(
            "SENTINEL_DOCKER_PRUNE_ENABLED", ""
        ).strip().lower() in {"1", "true", "yes", "on"}
        if not prune_enabled:
            logger.warning(
                "[sentinel][disk] automatic Docker pruning is disabled; "
                "set SENTINEL_DOCKER_PRUNE_ENABLED=true only when this "
                "process has approved Docker daemon access"
            )
            return True

        docker_binary = shutil.which("docker")
        if docker_binary is None:
            logger.error(
                "[sentinel][disk] Docker pruning is enabled, but the "
                "docker CLI is unavailable"
            )
            return True

        docker_host = os.environ.get("DOCKER_HOST")
        if not docker_host and not os.path.exists("/var/run/docker.sock"):
            logger.error(
                "[sentinel][disk] Docker pruning is enabled, but no "
                "Docker daemon endpoint is available"
            )
            return True

        result = await asyncio.to_thread(
            subprocess.run,
            [
                docker_binary,
                "system",
                "prune",
                "-f",
                "--filter",
                "until=1440h",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "no output").strip()
            detail = " ".join(detail.split())[:500]
            logger.error(
                f"[sentinel][disk] Docker prune failed with exit code "
                f"{result.returncode}: {detail}"
            )
            return True

        new_usage = shutil.disk_usage(target_path)
        new_percent = (new_usage.used / new_usage.total) * 100
        logger.info(
            f"[sentinel][disk] after prune: {new_percent:.1f}% "
            f"(freed {(usage.used - new_usage.used) / 1e9:.2f} GB)"
        )
        return new_percent >= threshold_percent
    except Exception as exc:
        logger.error(f"[sentinel][disk] disk watchdog error: {exc}")
        return True
