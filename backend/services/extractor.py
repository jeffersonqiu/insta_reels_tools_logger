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


CAPTION_NAME_RULES = (
    "Instagram captions are written by the creator and often spell product names correctly.\n"
    "When a caption is provided below:\n"
    "- If the caption clearly names a tool, product, or brand that matches something discussed in the audio "
    "(same product, even if the transcript mis-hears it), use the caption's exact spelling and casing for "
    'the JSON "name" field.\n'
    "- Example: caption says \"ruflo\" but the transcript says \"ruflow\" → use \"ruflo\".\n"
    "- If the caption has no usable tool names (only emojis, generic text, or hashtags with no product name), "
    "infer names from the transcript only.\n"
    "- Do not copy unrelated hashtags as tool names unless they are clearly the product being featured.\n"
)


def _build_extraction_user_prompt(transcript: str, caption: str | None) -> str:
    t = (transcript or "").strip()
    body = f"## AUDIO TRANSCRIPT (speech-to-text)\n{t}"
    if caption and caption.strip():
        body += f"\n\n## INSTAGRAM CAPTION (post text)\n{caption.strip()}"
    else:
        body += "\n\n## INSTAGRAM CAPTION\n(not available or empty — use transcript-only for names.)"
    return body


def _call_claude(user_prompt: str, force_json_retry: bool = False) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    retry_note = "\nIMPORTANT: return only raw JSON array output." if force_json_retry else ""
    system_prompt = (
        "You extract AI tool records from Reel content.\n"
        "You may receive both an audio transcript and an optional Instagram caption.\n"
        f"{CAPTION_NAME_RULES}\n"
        "Identify all distinct AI tools or AI product upgrades mentioned in the reel.\n"
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
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in msg.content if getattr(block, "text", None))


def extract_tools_from_transcript(transcript: str, caption: str | None = None) -> list[ToolExtraction]:
    if not settings.anthropic_api_key:
        raise ExtractionError("ANTHROPIC_API_KEY is missing.")

    user_prompt = _build_extraction_user_prompt(transcript, caption)
    first = _call_claude(user_prompt, force_json_retry=False)
    for idx, raw in enumerate((first, _call_claude(user_prompt, force_json_retry=True))):
        try:
            payload = json.loads(raw)
            if not isinstance(payload, list):
                raise ValueError("Expected a JSON array.")
            return [ToolExtraction.model_validate(item) for item in payload]
        except Exception:
            if idx == 1:
                raise ExtractionError(f"Failed to parse extraction JSON. Raw output: {raw}")
    return []
