"""Validate/import reviewed stored transcripts. Dry-run unless --apply is given."""
import argparse
import json
import sys
from pathlib import Path
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=False)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from db.client import get_supabase
    from services.reviewed_import import import_reviewed
    try:
        result = import_reviewed(get_supabase(), json.loads(args.input.read_text()), apply=args.apply)
    except Exception as exc:
        print(json.dumps({'ok':False, 'error_type':type(exc).__name__}))
        return 1
    print(json.dumps({'ok':True, 'applied':args.apply, **result}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
