import logging
import os
import subprocess
import time

from dotenv import load_dotenv

load_dotenv()

PLUGINS_DIR = os.getenv("PLUGINS_DIR")

logger = logging.getLogger(__name__)


def plugin_search(plugin_id: int) -> str | None:
    """Ripgrep the plugins mirror for `script_id(<plugin_id>)`.

    Returns the matching .nasl path, or None if no plugin has that ID.
    """
    if not PLUGINS_DIR:
        raise RuntimeError("PLUGINS_DIR is not set - check .env")

    command = f"script_id({plugin_id})"
    started = time.monotonic()
    logger.info("search started plugin_id=%s", plugin_id)
    proc = subprocess.Popen(
        ["rg", "-F", "-l", "-g", "*.nasl", command, PLUGINS_DIR],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        path = proc.stdout.readline().rstrip("\n")
    finally:
        proc.stdout.close()
        try:
            proc.terminate()
        except ProcessLookupError:
            pass
        stderr = proc.stderr.read()
        proc.stderr.close()
        proc.wait()

    duration = time.monotonic() - started

    if path:
        logger.info(
            "search hit plugin_id=%s path=%s duration=%.2fs", plugin_id, path, duration
        )
        return path

    if proc.returncode not in (0, 1):
        logger.error(
            "search failed plugin_id=%s returncode=%s stderr=%s",
            plugin_id, proc.returncode, stderr.strip(),
        )
        raise RuntimeError(f"ripgrep failed (exit {proc.returncode}): {stderr.strip()}")

    logger.info("search miss plugin_id=%s duration=%.2fs", plugin_id, duration)
    return None
