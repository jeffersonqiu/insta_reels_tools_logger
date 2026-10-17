"""Run a bounded batch of queued Reels; --dry-run never processes or writes."""

import argparse
import json
import logging
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import settings
from db.client import get_supabase
from services.queue_worker import run_queue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--video-id", type=UUID)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.limit <= 10:
        parser.error("--limit must be between 1 and 10")
    required = ["supabase_url", "supabase_service_key"]
    if not args.dry_run:
        required += ["anthropic_api_key", "assemblyai_api_key"]
    missing = [name.upper() for name in required if not getattr(settings, name)]
    if missing:
        parser.error("Missing configuration: " + ", ".join(missing))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = run_queue(get_supabase(), limit=args.limit,
                       video_id=str(args.video_id) if args.video_id else None, dry_run=args.dry_run)
    print(json.dumps(result, sort_keys=True))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
