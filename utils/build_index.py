import json
import re
import subprocess


def build_index(plugins_dir: str, out_path: str | None = None) -> dict:
    """Scan plugins_dir once and return {plugin_id: path}.

    If out_path is given, also writes the dict there as JSON.
    """
    out = subprocess.run(
        ["grep", "-roH", "--include=*.nasl", r"script_id([0-9]*)", plugins_dir],
        capture_output=True, text=True,
    )

    index = {}
    line_re = re.compile(r"^(.*?):script_id\((\d+)\)")
    for line in out.stdout.splitlines():
        m = line_re.match(line)
        if m:
            path, pid = m.group(1), m.group(2)
            index[pid] = path

    if out_path:
        with open(out_path, "w") as f:
            json.dump(index, f, indent=2)

    return index


if __name__ == "__main__":
    idx = build_index("/opt/nessus/lib/nessus/plugins/", "plugin_index.json")
    print(f"Indexed {len(idx)} plugins")