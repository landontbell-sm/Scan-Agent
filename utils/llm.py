import json
import logging
import os
import time

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from utils.models import TechBrief

load_dotenv()

logger = logging.getLogger(__name__)

# Async client (rather than the sync one) so respond() can stream tokens back
# to the caller as they're generated instead of blocking until the whole
# tech_brief is done - see respond()'s on_delta parameter.
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("ANTHROPIC_LLM_MODEL")

# output_config.format needs additionalProperties: false to constrain
# generation to exactly this shape; model_json_schema() doesn't set that by
# default. Built once at import time rather than per-call.
_TECH_BRIEF_SCHEMA = TechBrief.model_json_schema()
_TECH_BRIEF_SCHEMA["additionalProperties"] = False

SYSTEM_PROMPT = [
    {
        "type": "text",
        "text": (
            "You are an expert Nessus scan technician and SOC analyst with deep "
            "knowledge of Nessus plugins, NASL syntax, and how Nessus findings "
            "translate to real customer risk. Explain findings precisely and "
            "conservatively: never invent a payload, command, or match condition "
            "you can't point to in the source you're given, and never contradict "
            "facts already provided to you as deterministic. Quote source lines "
            "verbatim when citing them."
        ),
        "cache_control": {"type": "ephemeral"},
    }
]


async def respond(prompt: str, on_delta=None) -> TechBrief:
    """Stream a TechBrief out of the model.

    on_delta, if given, is awaited with each raw text chunk as it streams in
    (the tech_brief JSON as it's generated) - callers use this to show live
    progress instead of a silent wait for the whole response.
    """
    started = time.monotonic()
    logger.info("llm request started model=%s prompt_chars=%d", MODEL, len(prompt))

    async with client.messages.stream(
        model=MODEL,
        max_tokens=8192,
        # Disabled rather than the Sonnet 5 default (adaptive): this task is
        # read-and-quote, not multi-step math, and the tech is waiting live
        # on the phone - the latency isn't worth it here.
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": _TECH_BRIEF_SCHEMA}},
    ) as stream:
        async for delta in stream.text_stream:
            if on_delta is not None:
                await on_delta(delta)
        msg = await stream.get_final_message()

    logger.info(
        "llm request done model=%s stop_reason=%s input_tokens=%s output_tokens=%s "
        "cache_read_tokens=%s duration=%.2fs",
        MODEL,
        msg.stop_reason,
        msg.usage.input_tokens,
        msg.usage.output_tokens,
        msg.usage.cache_read_input_tokens,
        time.monotonic() - started,
    )

    if msg.stop_reason == "refusal":
        # Explaining injection/exploit payloads is this app's whole job, so a
        # cyber-category classifier decline is a real, expected outcome here -
        # not a bug. Surface it plainly instead of a confusing parse failure.
        category = msg.stop_details.category if msg.stop_details else None
        logger.warning("llm refusal category=%s", category)
        raise RuntimeError(f"Model declined to respond (refusal category: {category})")

    text = next((b.text for b in msg.content if b.type == "text"), None)
    if text is None:
        raise RuntimeError("Model response didn't match the expected TechBrief shape")

    try:
        return TechBrief.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValidationError) as e:
        raise RuntimeError(f"Model response didn't match the expected TechBrief shape: {e}") from e
