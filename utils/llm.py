import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("ANTHROPIC_LLM_MODEL")

SYSTEM_PROMPT = [
    {
        "type": "text",
        "text": "You are an expert Nessus Scan Tech / SOC Analyst with deep knowledge of Nessus Plugins systems...",
        "cache_control": {"type": "ephemeral"},
    }
]

def respond(prompt: str) -> str:
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")