"""Inspect/register the bot through the backend; its token stays on Railway."""

import argparse
import json
import sys
from pathlib import Path

import httpx
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import _strip_secret, settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api-base-url', required=True)
    parser.add_argument('--bot-username', required=True)
    parser.add_argument('--env-file', type=Path, help='Optional local env file supplying WEBHOOK_SECRET only')
    parser.add_argument('--register', action='store_true', help='Register the HTTPS backend webhook after inspection')
    args = parser.parse_args()
    secret = settings.webhook_secret
    if args.env_file:
        secret = _strip_secret(dotenv_values(args.env_file).get('WEBHOOK_SECRET') or '')
    if not secret:
        parser.error('WEBHOOK_SECRET is missing')
    if not args.api_base_url.startswith('https://'):
        parser.error('Use the HTTPS production API origin')
    try:
        response = httpx.post(args.api_base_url.rstrip('/') + '/api/telegram/setup', timeout=60, json={
            'secret': secret, 'expected_username': args.bot_username,
            'operation': 'register' if args.register else 'inspect',
            'public_api_url': args.api_base_url if args.register else None,
        })
        if response.status_code != 200:
            print(json.dumps({'http_status': response.status_code, 'detail': response.json().get('detail', 'Setup failed')}))
            return 1
        print(json.dumps(response.json(), indent=2))
        return 0
    except Exception:
        print('Could not contact the backend setup endpoint. No credentials were printed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
