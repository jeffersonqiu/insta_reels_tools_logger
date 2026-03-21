import json

from anthropic import Anthropic

from config import settings
from models.schemas import ToolExtraction

ALLOWED_TAGS = [
    "coding",
    "claude code",
    "image generation",
    "video generation",
    "audio",
    "productivity",
    "agents",
    "rag",
    "search",
    "multimodal",
    "harness engineering",
    "data",
    "devtools",
]


class ExtractionError(Exception):
    pass


def _call_claude(prompt: str, force_json_retry: bool = False) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    retry_note = "\nIMPORTANT: return only raw JSON array output." if force_json_retry else ""
    system_prompt = (
        "You extract AI tool records from transcripts.\n"
        "Identify all distinct AI tools or AI product upgrades.\n"
        "Return only a JSON array of objects with keys: name, functionality, problem_solved, tags.\n"
        f"Prefer tags from this list: {ALLOWED_TAGS}.\n"
        "If no listed tag fits, you may use a novel free-form tag.\n"
        "No markdown fences, no preamble."
        + retry_note
    )
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in msg.content if getattr(block, "text", None))


def extract_tools_from_transcript(transcript: str) -> list[ToolExtraction]:
    if not settings.anthropic_api_key:
        raise ExtractionError("ANTHROPIC_API_KEY is missing.")

    first = _call_claude(transcript, force_json_retry=False)
    for idx, raw in enumerate((first, _call_claude(transcript, force_json_retry=True))):
        try:
            payload = json.loads(raw)
            if not isinstance(payload, list):
                raise ValueError("Expected a JSON array.")
            return [ToolExtraction.model_validate(item) for item in payload]
        except Exception:
            if idx == 1:
                raise ExtractionError(f"Failed to parse extraction JSON. Raw output: {raw}")
    return []
