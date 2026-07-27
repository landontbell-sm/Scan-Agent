# Chainlit entrypoint

import logging
import time

import chainlit as cl

from tools.explain import explain_plugin
from tools.extract import extract
from tools.search import plugin_search
from utils.models import TechBrief

# force=True: chainlit/uvicorn may already have handlers on the root logger
# by the time this module loads, and basicConfig() is a no-op in that case
# without it - this is the one place logging is configured for the app.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)

# search/extract are blocking (subprocess, file I/O) - run off the event
# loop. explain_plugin is native async (it streams), so it's awaited directly.
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
    started = time.monotonic()
    logger.info("lookup requested plugin_id=%s", plugin_id)

    async with cl.Step(name="Search", type="tool") as step:
        step.input = f"script_id({plugin_id})"
        try:
            path = await search_async(plugin_id)
        except RuntimeError as e:
            step.output = f"Search failed: {e}"
            await cl.Message(content=f"Search failed: {e}").send()
            return

        if path is None:
            step.output = "No matching plugin found."
            await cl.Message(content=f"No `.nasl` plugin found for ID {plugin_id}.").send()
            return

        step.output = path

    async with cl.Step(name="Extract", type="tool") as step:
        step.input = path
        data = await extract_async(path)
        step.output = (
            f"severity={data['severity'] or 'unknown'}, "
            f"detection_style={data['fp_signals']['detection_style']}"
        )

    # Deterministic facts don't need the model - send them the moment
    # they're available instead of holding them behind the LLM call.
    await cl.Message(content=format_deterministic_facts(plugin_id, data)).send()

    async with cl.Step(name="Explain", type="llm") as step:
        step.input = "Reading plugin source to explain the trigger logic and FP risk…"

        async def on_delta(delta: str) -> None:
            await step.stream_token(delta)

        try:
            brief = await explain_plugin(data, on_delta=on_delta)
        except RuntimeError as e:
            await cl.Message(content=f"Couldn't generate an explanation: {e}").send()
            return

    await cl.Message(content=format_brief(data, brief)).send()

    logger.info(
        "lookup done plugin_id=%s duration=%.2fs", plugin_id, time.monotonic() - started
    )


def format_deterministic_facts(plugin_id: int, data: dict) -> str:
    """Facts extract() already gives us outright - rendered directly, never
    routed through the model, and sent before the LLM call even starts.
    """
    meta = data["metadata"]

    def first_attr(name: str) -> str | None:
        values = meta["attributes"].get(name)
        return values[0] if values else None

    facts = [
        f"- **Severity:** {data['severity'] or 'unknown'}",
        f"- **Category:** {meta['category'] or '-'}",
        f"- **Family:** {meta['family'] or '-'}",
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
    sections.append("_Asking the model to explain the trigger logic and false-positive risk…_")
    return "\n\n".join(sections)


def format_brief(data: dict, brief: TechBrief) -> str:
    """The two fields that need real comprehension - rendered once the model
    has produced them, plus the raw source for the tech to verify against.
    """
    sections = [
        f"**Detection reliability:** {brief.detection_reliability}",
        f"**What it does:** {brief.summary}",
        f"**False-positive analysis:** {brief.fp_analysis}",
        f"### Raw plugin source\n```\n{data['raw']}\n```",
    ]
    return "\n\n".join(sections)
