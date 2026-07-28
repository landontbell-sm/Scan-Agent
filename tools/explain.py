import logging
from pathlib import Path
from utils.llm import respond
from utils.models import TechBrief

logger = logging.getLogger(__name__)

_CHEATSHEET_PATH = Path(__file__).resolve().parent.parent / "utils" / "cheatsheet.md"


def _format_attributes(attributes: dict) -> str:
    if not attributes:
        return "(none found)"
    return "\n".join(
        f"- {name}: {value}" for name, values in attributes.items() for value in values
    )

def build_prompt(data: dict) -> str:
    metadata = data["metadata"]
    fp = data["fp_signals"]
    cheatsheet = _CHEATSHEET_PATH.read_text()

    return f"""A Nessus scan technician is on the phone with a customer and needs to
understand this finding. Everything under "Deterministic facts" and "Tenable's
own writeup" below was extracted mechanically from the plugin's source - treat it
as ground truth, never contradict or regenerate it. Your job is the one part that
needs real reading: what the plugin injects/checks and what response makes it fire.

# NASL cheat sheet
{cheatsheet}

# Deterministic facts (already extracted - do not regenerate these)
- Plugin ID: {metadata['script_id']}
- Name: {metadata['script_name']}
- Family: {metadata['family']}
- Category: {metadata['category']}
- Severity: {data['severity']}
- CVEs: {', '.join(metadata['cve_ids']) or 'none'}
- CWEs: {', '.join(metadata['cwe_ids']) or 'none'}
- Paranoid-only: {fp['paranoid_only']} (threshold {fp['paranoia_threshold']})
- Other AUDIT_* bailouts: {', '.join(fp['audit_bailouts']) or 'none'}
- Detection style (heuristic, may be "unknown"): {fp['detection_style']}

# Tenable's own writeup (lift verbatim where relevant, don't paraphrase away specifics)
{_format_attributes(metadata['attributes'])}

# Plugin source (runtime logic - read this for the trigger mechanism)
```
{data['body']}
```

Produce a TechBrief for this finding. Use the deterministic facts and cheat sheet
above as context, not as something to re-derive - your own read of the source is
what fills in the fields that need real comprehension.
"""


async def explain_plugin(data: dict, on_delta=None) -> TechBrief:
    prompt = build_prompt(data)
    logger.info(
        "explain prompt built plugin_id=%s prompt_chars=%d",
        data["metadata"]["script_id"],
        len(prompt),
    )
    return await respond(prompt, on_delta=on_delta)
