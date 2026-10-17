"""Opt-in backfill: create knowledge_items for completed videos that have none.

Uses stored transcript/caption only (Anthropic calls; no AssemblyAI, no Instagram). NOT run on deploy.
Does not touch tools/video_tools.

  cd backend
  uv run python scripts/backfill_knowledge_items.py --dry-run          # list candidates, no cost
  uv run python scripts/backfill_knowledge_items.py --limit 3          # process 3 videos
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.client import get_supabase
from services.extractor import extract_knowledge
from services.knowledge import upsert_knowledge_item


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.limit < 1:
        ap.error("--limit must be at least 1")

    sb = get_supabase()
    done = {r["video_id"] for r in sb.table("knowledge_items").select("video_id").execute().data or []}
    videos = (
        sb.table("videos")
        .select("id,instagram_url,canonical_url,transcript,caption")
        .eq("status", "completed")
        .order("processed_at", desc=True)
        .execute()
        .data
        or []
    )
    todo = [v for v in videos if v["id"] not in done and (v.get("transcript") or "").strip()]
    print(f"{len(todo)} completed videos without a knowledge item (processing up to {args.limit}).")
    for v in todo[: args.limit]:
        url = v.get("canonical_url") or v["instagram_url"]
        if args.dry_run:
            print(f"  would process {v['id']} {url}")
            continue
        try:
            ext = extract_knowledge(v["transcript"], caption=v.get("caption"))
            item_id = upsert_knowledge_item(sb, v["id"], url, ext)
            print(f"  ok {v['id']} -> {item_id} ({ext.title!r})")
        except Exception as exc:
            print(f"  FAILED {v['id']}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
