# Step 9: private Telegram Q&A

Use the existing FastAPI service on Railway; a separate polling service is unnecessary. The selected bot is `@jeqiu_insta_reel_bot`. Its token belongs only in Railway's `TELEGRAM_BOT_TOKEN`, never in source code, GitHub files, browser URLs, or chat.

## Setup

1. Apply `backend/db/migrations/006_telegram_updates.sql` before deploying the feature. Run `backend/db/verification/006_telegram_updates.sql`; all five checks must be true. This adds a metadata-only deduplication table, without changing existing records. RLS blocks client roles; the backend uses its existing service key.
2. Add the BotFather token to the existing Railway service's `TELEGRAM_BOT_TOKEN` variable and deploy it. No GitHub Actions secret is needed for Telegram Q&A.
3. Publish/test/deploy the backend. Inspect the token without retrieving it from Railway:

   ```sh
   cd backend
   uv run python scripts/configure_telegram.py --api-base-url https://instareelstoolslogger-production.up.railway.app --bot-username jeqiu_insta_reel_bot
   ```

   The script uses the existing local `WEBHOOK_SECRET` to call an authenticated backend setup endpoint. `--env-file PATH` optionally supplies that existing secret. The Telegram bot token stays on Railway. Inspection only calls `getMe` and `getWebhookInfo`.
4. Repeat with `--register` to register `https://instareelstoolslogger-production.up.railway.app/api/webhook/telegram`. Setup verifies the bot username before any change. It uses Telegram's secret header, derived from the existing administrator secret using HMAC-SHA256 with a dedicated purpose label. No new manual webhook credential is required. If `WEBHOOK_SECRET` changes, register again. Existing pending updates are preserved.
5. Open the bot in Telegram and send `/start`. It replies with **your own numeric Telegram user ID**. Add that number to Railway `TELEGRAM_ALLOWED_USER_IDS` and deploy. The value can contain comma-separated IDs if intentionally sharing with other users. An empty value denies all knowledge access and Reel submission; `/start` only returns the requesting user's own ID and setup instructions.
6. Optionally set `PUBLIC_APP_URL=https://insta-reels-tools-logger.jeffersonqiu1.workers.dev` for Library citation links. Otherwise citations link to the stored source Reels.
7. Send `/recent`, then `/ask What is OpenFlow and what could I try?`. Verify a reply with the saved source. Only private chats with an allowed sender are accepted; group/channel messages are ignored even from an allowed user.

[Telegram documents the secret header and webhook setup](https://core.telegram.org/bots/api#setwebhook). Stop any legacy polling instance before registering a webhook: Telegram does not support polling and an active outgoing webhook together. The optional `run_telegram_bot` entry point uses the same authorization/deduplication logic and requires the backend configuration/database credentials when used locally.

## Use and limits

- Share a Reel URL to use the existing canonical ingestion queue and failed-video retry behavior. Repeated links preserve the saved video ID. This does not automatically run a paid historical backfill.
- `/recent` lists the newest five knowledge items without an LLM call.
- `/help` explains usage. `/ask <question>` or ordinary text asks a question. Questions are limited to 1,500 characters; they do not retain conversation history.
- Retrieval scans saved knowledge using keyword overlap, favoring titles and tags, and chooses at most five items. This is a personal-library keyword retriever, not semantic search. Legacy Tools records without a knowledge item are not automatically included.
- The answer uses at most 18,000 characters of item context and one Anthropic request (`max_tokens=900`, timeout 30 seconds, automatic retries disabled). Model responses must cite supplied item IDs. Unknown/missing citations or invalid JSON fail with a generic retry instruction, without printing raw provider output. No relevant knowledge means no LLM call.
- Answers contain only saved-source context, with an explicit instruction to abstain when insufficient. Source content and questions are treated as untrusted data. LLM grounding is not a proof of factual correctness; sources are provided for review.
- HTTP(S) citation links come from configured Library URLs or stored source URLs. Model-generated URLs are removed. Telegram replies use plain text and disabled link previews, split within the UTF-16 length limit when necessary.
- `telegram_updates` stores only update ID, status, error class and timestamps. It contains no question text, chat ID, user ID or credentials. A primary key claims a delivery before processing, so duplicates do not repeat paid work or replies.
- Webhooks acknowledge after the durable claim, then answer in a background task. A process interruption can leave a claim in `processing`; it is not automatically retried, because a provider may already have charged. Resend a new message to retry deliberately. The metadata table is a deduplication ledger, not a durable question job queue.
- Bot tokens in HTTP transport logs are redacted; provider exception text is not echoed to Telegram or saved in the event table. The setup endpoint uses the existing administrator secret and returns metadata only.

## Verification and rollback

Run the complete backend suite with `uv run pytest`. Tests block external network access and mock Telegram/Anthropic/Supabase. They cover authorization before work, empty allowlists, private chat enforcement, claims and duplicate deliveries, queue reuse, bounded/no-cost requests, bot identity verification, webhook registration, unsafe links, unknown citations, redaction, and Unicode reply limits.

To disable access immediately, clear `TELEGRAM_ALLOWED_USER_IDS` and deploy. Remove/rotate the bot token through BotFather only when needed. Existing Tools, knowledge items, Reel ingestion, frontend and GitHub worker are unaffected by the additional routes/table.

Token validation rejects malformed values (including embedded whitespace) before opening an HTTP connection. Transport logging redacts the entire Telegram URL credential segment, including percent-encoded values; setup errors expose only controlled messages or HTTP status codes. If a token has appeared in logs, revoke/regenerate it in BotFather before retrying.
