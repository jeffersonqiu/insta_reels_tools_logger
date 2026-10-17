import json

from anthropic import Anthropic

from config import settings
from models.schemas import KnowledgeExtraction, ToolExtraction

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


SYSTEM_PROMPT = (
    "You turn Instagram Reel content into a structured knowledge item.\n"
    "You receive an audio transcript and an optional Instagram caption. Use only what they contain.\n"
    f"{CAPTION_NAME_RULES}\n"
    "The reel may be about anything (AI tools, software architecture, research, tutorials, products, design, "
    "workflows). Always produce a useful knowledge item, even when no AI tool is present.\n"
    "Return ONE JSON object with exactly these keys:\n"
    "- title: short descriptive title\n"
    "- summary: 2-4 sentence concise summary\n"
    "- key_ideas: array of strings, the main takeaways\n"
    "- tools: array of objects {name, functionality, problem_solved, tags} for each distinct AI tool or AI "
    "product upgrade mentioned (functionality: 2-3 sentences; problem_solved: 1-2 concrete sentences for a "
    "developer/AI practitioner). Use [] if none.\n"
    "- repositories: array of objects {name, url, description} for GitHub repos or other named links/projects. "
    "Set url to null unless a URL is explicitly present in the transcript or caption; never invent URLs. Use [] if none.\n"
    "- concepts: array of strings, technical concepts or techniques explained\n"
    "- action_items: array of strings, concrete things the viewer could try or do\n"
    "- tags: array of strings\n"
    f"Prefer tags from this list: {ALLOWED_TAGS}. If none fit, you may use a novel free-form tag.\n"
    "Empty arrays are fine for any list. No markdown fences, no preamble."
)


def _call_claude(user_prompt: str, force_json_retry: bool = False) -> str:
    client = Anthropic(api_key=settings.anthropic_api_key)
    retry_note = "\nIMPORTANT: return only the raw JSON object, nothing else." if force_json_retry else ""
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=4000,
        system=SYSTEM_PROMPT + retry_note,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in msg.content if getattr(block, "text", None))


def _parse_knowledge(raw: str) -> KnowledgeExtraction:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    return KnowledgeExtraction.model_validate(payload)


def extract_knowledge(transcript: str, caption: str | None = None) -> KnowledgeExtraction:
    if not settings.anthropic_api_key:
        raise ExtractionError("ANTHROPIC_API_KEY is missing.")

    user_prompt = _build_extraction_user_prompt(transcript, caption)
    raw = _call_claude(user_prompt)
    try:
        return _parse_knowledge(raw)
    except Exception:
        pass
    raw = _call_claude(user_prompt, force_json_retry=True)
    try:
        return _parse_knowledge(raw)
    except Exception:
        raise ExtractionError(f"Failed to parse extraction JSON. Raw output: {raw}") from None


def extract_tools_from_transcript(transcript: str, caption: str | None = None) -> list[ToolExtraction]:
    """Legacy helper: tools only."""
    return extract_knowledge(transcript, caption).tools
