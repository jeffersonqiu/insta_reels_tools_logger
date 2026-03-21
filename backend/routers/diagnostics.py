"""
Pre-flight checks before running the full ingestion pipeline.
"""

from fastapi import APIRouter

from services.assemblyai_check import check_assemblyai_connection

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/assemblyai")
def assemblyai_status():
    """
    Step 1 — verify AssemblyAI API key and network before POST /api/webhook/reel.

    **Success:** `"ok": true` → proceed to webhook smoke test.
    **Failure:** read `message` + `hint`; fix `.env` and restart server.
    """
    return check_assemblyai_connection()


@router.get("/summary")
def diagnostics_summary():
    """
    Ordered checklist-style snapshot (extend later with Supabase ping, etc.).
    """
    assemblyai = check_assemblyai_connection()
    return {
        "steps": [
            {
                "id": 1,
                "name": "assemblyai",
                "label": "AssemblyAI API key & connectivity",
                "ok": assemblyai.get("ok"),
                "detail": assemblyai,
            },
        ],
        "all_ok": bool(assemblyai.get("ok")),
        "next_if_all_ok": "POST /api/webhook/reel with a public Reel URL and matching WEBHOOK_SECRET.",
    }
