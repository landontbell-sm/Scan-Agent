# Tools for the agent to get details about the plugins

import os
import subprocess
from dotenv import load_dotenv
import re

load_dotenv()

plugins_dir = os.getenv("PLUGINS_DIR")

def plugin_search(plugin_id: int):
    """Searches the local disk for the NASL file matching the plugin ID."""
    command = f"script_id({plugin_id})"
    try:
        out = subprocess.check_output(["rg", "-F", command, plugins_dir], text=True)
        return out.split(":", 1)[0] # return just the file path
    except Exception as e:
        print(f"An error has occured: {e}")
        return None

def extract_nasl(path: str):
    with open(path, "r") as file:
        content = file.read()

    header, _, body = content.partition("exit(0);")
    return {"header": header, "body": body, "raw": content}


def parse_header(header: str):
    header_info = {}
    id = re.search(r"script_id\((\d+)\);", header)
    version = re.search(r"script_version\(\"(.*?)\"\)", header)
    header_info["script_id"] = id.group(1) if id else None
    header_info["version"] = version.group(1) if version else None
    return header_info

def list_plugins() -> list:
    return os.listdir(plugins_dir)

if __name__ == "__main__":
    try:
        plugin = 39465
        output = plugin_search(plugin)
        content = extract_nasl(output)
        print(parse_header(content["header"]))

    except Exception as e:
        print(f"An error has occured: {e}")