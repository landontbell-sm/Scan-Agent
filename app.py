# Chainlit entrypoint
#
# tools/explain.py + utils/llm.py (the LLM pass) aren't written yet, so this
# runs search -> extract only and shows the raw deterministic extraction as
# a stand-in brief - enough to verify search/extract work end to end in the
# actual UI. Swap in the real tech_brief once explain.py exists.

import chainlit as cl

from tools.extract import extract
from tools.search import plugin_search

search_async = cl.make_async(plugin_search)
extract_async = cl.make_async(extract)


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
    await cl.Message(content=format_interim_brief(plugin_id, path, data)).send()


def format_interim_brief(plugin_id: int, path: str, data: dict) -> str:
    meta = data["metadata"]
    fp = data["fp_signals"]

    def first_attr(name: str) -> str:
        values = meta["attributes"].get(name)
        return values[0] if values else "-"

    paranoid = f"yes (threshold {fp['paranoia_threshold']})" if fp["paranoid_only"] else "no"

    return "\n".join(
        [
            f"**Plugin {plugin_id} — {meta['script_name'] or 'unknown'}**",
            f"`{path}`",
            "",
            f"- Severity: {data['severity'] or 'unknown'}",
            f"- Category: {meta['category'] or '-'}",
            f"- Detection style: {fp['detection_style']}",
            f"- Paranoid-only: {paranoid}",
            f"- Audit bailouts: {', '.join(fp['audit_bailouts']) or 'none'}",
            f"- CVEs: {', '.join(meta['cve_ids']) or 'none'}",
            f"- CWEs: {', '.join(meta['cwe_ids']) or 'none'}",
            "",
            f"**Synopsis:** {first_attr('synopsis')}",
            f"**Solution:** {first_attr('solution')}",
            "",
            "_Raw deterministic extraction only — the LLM explanation pass "
            "(`tools/explain.py`) isn't wired in yet._",
        ]
    )
