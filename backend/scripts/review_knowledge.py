"""Produce a no-cost snapshot for the weekly knowledge organization review."""
import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from db.client import get_supabase
    from services.knowledge_repository import _rows, ITEM_FIELDS, VIDEO_FIELDS
    from services.organization import review_snapshot
    try:
        db = get_supabase()
        items = _rows(db, 'knowledge_items', ITEM_FIELDS)
        videos = _rows(db, 'videos', VIDEO_FIELDS)
        snapshot = review_snapshot(items)
        covered = {item['video_id'] for item in items}
        snapshot['missing_knowledge_items'] = [{'video_id':video['id'], 'has_transcript':bool(video.get('transcript'))} for video in videos if video['id'] not in covered and video.get('status') == 'completed']
        snapshot['unfinished_video_count'] = sum(video.get('status') != 'completed' for video in videos)
    except Exception as exc:
        print(json.dumps({'ok':False, 'error_type':type(exc).__name__}))
        return 1
    encoded = json.dumps(snapshot, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    else:
        print(encoded)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
