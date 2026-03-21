"""
Structured AssemblyAI connectivity check (no reel download, no transcription job).

Uses the REST API list-transcripts endpoint with limit=1 to validate the API key.
See: https://www.assemblyai.com/docs/api-reference/transcript
"""

from typing import Any

import httpx

from config import settings

ASSEMBLYAI_TRANSCRIPT_LIST = "https://api.assemblyai.com/v2/transcript"


def check_assemblyai_connection(*, timeout_seconds: float = 15.0) -> dict[str, Any]:
    """
    Returns a stable dict for JSON responses and logging.
    Never includes the API key.
    """
    key = (settings.assemblyai_api_key or "").strip()
    if not key:
        return {
            "service": "assemblyai",
            "configured": False,
            "reachable": None,
            "http_status": None,
            "ok": False,
            "message": "ASSEMBLYAI_API_KEY is missing or empty in environment.",
            "hint": "Set ASSEMBLYAI_API_KEY in backend/.env and restart uvicorn.",
        }

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(
                ASSEMBLYAI_TRANSCRIPT_LIST,
                headers={"Authorization": key},
                params={"limit": 1},
            )
    except httpx.TimeoutException:
        return {
            "service": "assemblyai",
            "configured": True,
            "reachable": False,
            "http_status": None,
            "ok": False,
            "message": "Request to AssemblyAI timed out.",
            "hint": "Check network, firewall, or try again.",
        }
    except httpx.RequestError as exc:
        return {
            "service": "assemblyai",
            "configured": True,
            "reachable": False,
            "http_status": None,
            "ok": False,
            "message": f"Could not reach AssemblyAI: {exc!s}",
            "hint": "Check network / DNS / proxy.",
        }

    if response.status_code == 401:
        return {
            "service": "assemblyai",
            "configured": True,
            "reachable": True,
            "http_status": 401,
            "ok": False,
            "message": "AssemblyAI rejected the API key (401 Unauthorized).",
            "hint": "Copy the key from AssemblyAI dashboard; remove quotes/spaces; restart uvicorn.",
        }

    if response.status_code == 403:
        return {
            "service": "assemblyai",
            "configured": True,
            "reachable": True,
            "http_status": 403,
            "ok": False,
            "message": "AssemblyAI returned 403 Forbidden.",
            "hint": "Key may lack permission or account billing/plan issue — check AssemblyAI dashboard.",
        }

    if response.status_code >= 400:
        body_preview = (response.text or "")[:300]
        return {
            "service": "assemblyai",
            "configured": True,
            "reachable": True,
            "http_status": response.status_code,
            "ok": False,
            "message": f"AssemblyAI returned HTTP {response.status_code}.",
            "hint": body_preview or "See AssemblyAI status page or docs.",
        }

    return {
        "service": "assemblyai",
        "configured": True,
        "reachable": True,
        "http_status": response.status_code,
        "ok": True,
        "message": "API key accepted; AssemblyAI transcript API responded successfully.",
        "hint": "Safe to run the full reel pipeline (download → transcribe → extract).",
    }
