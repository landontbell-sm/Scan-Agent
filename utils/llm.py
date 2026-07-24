import os
from dotenv import load_dotenv
from anthropic import Anthropic

from utils.models import TechBrief

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("ANTHROPIC_LLM_MODEL")

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


def respond(prompt: str) -> TechBrief:
    msg = client.messages.parse(
        model=MODEL,
        max_tokens=8192,
        # Disabled rather than the Sonnet 5 default (adaptive): this task is
        # read-and-quote, not multi-step math, and the tech is waiting live
        # on the phone - the latency isn't worth it here.
        thinking={"type": "disabled"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
        output_format=TechBrief,
    )

    if msg.stop_reason == "refusal":
        # Explaining injection/exploit payloads is this app's whole job, so a
        # cyber-category classifier decline is a real, expected outcome here -
        # not a bug. Surface it plainly instead of a confusing parse failure.
        category = msg.stop_details.category if msg.stop_details else None
        raise RuntimeError(f"Model declined to respond (refusal category: {category})")

    if msg.parsed_output is None:
        raise RuntimeError("Model response didn't match the expected TechBrief shape")

    return msg.parsed_output
