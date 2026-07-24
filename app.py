# Chainlit entrypoint

import chainlit as cl

from tools.explain import explain_plugin
from tools.extract import extract
from tools.search import plugin_search
from utils.models import TechBrief

search_async = cl.make_async(plugin_search)
extract_async = cl.make_async(extract)
explain_async = cl.make_async(explain_plugin)


@cl.on_chat_start
async def start():
    await cl.Message(
        content="**AI Scan Assistant**\n\nEnter a Nessus plugin ID to look it up (e.g. `39465`)."
    ).send()


@cl.on_message
async def main(message: cl.Message):
    text = message.content.strip()
    if not text.isdigit():
        await cl.Message(content=f"`{text}` isn't a plugin ID — enter a number.").send()
        return

    plugin_id = int(text)

    try:
        path = await search_async(plugin_id)
    except RuntimeError as e:
        await cl.Message(content=f"Search failed: {e}").send()
        return

    if path is None:
        await cl.Message(content=f"No `.nasl` plugin found for ID {plugin_id}.").send()
        return

    data = await extract_async(path)

    try:
        brief = await explain_async(data)
    except RuntimeError as e:
        await cl.Message(content=f"Couldn't generate an explanation: {e}").send()
        return

    await cl.Message(content=format_tech_brief(plugin_id, data, brief)).send()


def format_tech_brief(plugin_id: int, data: dict, brief: TechBrief) -> str:
    """Deterministic facts render directly from extract()'s output - never
    routed through the model, which only supplies `summary` and `fp_analysis`.
    """
    meta = data["metadata"]

    def first_attr(name: str) -> str | None:
        values = meta["attributes"].get(name)
        return values[0] if values else None

    facts = [
        f"- **Severity:** {data['severity'] or 'unknown'}",
        f"- **Category:** {meta['category'] or '-'}",
        f"- **Family:** {meta['family'] or '-'}",
        f"- **Detection reliability:** {brief.detection_reliability}",
        f"- **CVEs:** {', '.join(meta['cve_ids']) or 'none'}",
        f"- **CWEs:** {', '.join(meta['cwe_ids']) or 'none'}",
    ]
    if meta["cvss_vector"]:
        facts.append(f"- **CVSS:** {meta['cvss_vector']}")
    if meta["script_version"]:
        facts.append(f"- **Plugin version:** {meta['script_version']}")
    if meta["xrefs"]:
        xref_str = ", ".join(f"{x['name']}: {x['value']}" for x in meta["xrefs"])
        facts.append(f"- **Xrefs:** {xref_str}")

    solution = first_attr("solution")

    sections = [
        f"## Plugin {plugin_id} — {meta['script_name'] or 'unknown'}",
        "\n".join(facts),
    ]
    if solution:
        sections.append(f"**Tenable's solution:** {solution}")
    sections += [
        f"**What it does:** {brief.summary}",
        f"**False-positive analysis:** {brief.fp_analysis}",
        f"### Raw plugin source\n```\n{data['raw']}\n```",
    ]
    return "\n\n".join(sections)
