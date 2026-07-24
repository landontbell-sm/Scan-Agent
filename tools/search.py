# Locate a plugin's .nasl file by ID. Extracting content from that file is
# tools/extract.py's job, not this one - see it for header/body parsing.

import os
import subprocess

from dotenv import load_dotenv

load_dotenv()

PLUGINS_DIR = os.getenv("PLUGINS_DIR")


def plugin_search(plugin_id: int) -> str | None:
    """Ripgrep the plugins mirror for `script_id(<plugin_id>)`.

    Returns the matching .nasl path, or None if no plugin has that ID.
    """
    if not PLUGINS_DIR:
        raise RuntimeError("PLUGINS_DIR is not set - check .env")

    command = f"script_id({plugin_id})"
    try:
        # -l: print matching file paths only, one per line - no need to
        # parse "path:line:content" out of ripgrep's normal match format.
        out = subprocess.check_output(["rg", "-F", "-l", command, PLUGINS_DIR], text=True)
        return out.splitlines()[0]
    except subprocess.CalledProcessError:
        # ripgrep exits 1 for "no matches" - that's an expected miss, not an
        # error. Anything else (missing PLUGINS_DIR path, rg not installed,
        # permission errors) should raise instead of silently looking like
        # "plugin not found."
        return None


if __name__ == "__main__":
    import sys

    plugin_id = int(sys.argv[1]) if len(sys.argv) > 1 else 39465
    print(plugin_search(plugin_id))
