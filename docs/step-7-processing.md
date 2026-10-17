# Step 7: GitHub Actions processing

The webhook still canonicalizes and persists each Reel before returning its video ID. With `PROCESSING_MODE=github_actions`, it leaves the row queued for an ephemeral Actions runner. The worker uses the existing downloader, AssemblyAI transcription, knowledge extraction, and Tools persistence pipeline.

No schema migration is required. `PROCESSING_MODE` defaults to `inline` to preserve the deployed behavior until cutover is ready.

## Worker behavior

- `backend/scripts/process_queue.py` processes up to three queued videos by default; `--limit` accepts 1–10.
- Rows are selected oldest first. `--video-id UUID` optionally targets one queued record.
- `--dry-run` only reads candidates. It never downloads, transcribes, calls Anthropic, recovers stale jobs, or writes.
- Each attempt is claimed with a conditional update on video ID, queued status, and the observed attempt counter. Only the winner downloads or incurs processing costs.
- Completed/failed/in-flight videos are not automatically reprocessed. A failed Reel is explicitly requeued by the existing webhook when the user resubmits it.
- A claim left processing for over two hours is marked failed on the next real worker run. The workflow timeout is 30 minutes. Recovery does not automatically retry paid work or touch fresh jobs.
- A download/extraction/tool failure remains recorded on its source video, and the worker continues with the rest of its bounded batch. A batch with failures exits nonzero so Actions reports a failure.
- Knowledge items remain one per video. Existing Tools statuses and notes survive retries.

## Workflow controls

`.github/workflows/process-reels.yml` supports a schedule every five minutes, offset from the top of the hour, plus manual **Run workflow** inputs:

| Input | Default | Meaning |
| --- | --- | --- |
| `dry_run` | true for manual runs | Read candidates only |
| `batch_size` | 3 | At most 1–10 queued Reels |
| `video_id` | empty | Optional one queued video UUID |

Scheduled jobs are gated by the repository variable `PROCESSING_WORKER_ENABLED=true`. Without that variable, the scheduled processing job is skipped. Manual dispatch can run before enabling the schedule.

The workflow has a shared concurrency group, does not cancel a running batch, uses read-only repository permissions, pins actions by commit SHA, and exposes processing secrets only to the worker step. No cookies, audio, transcripts, or secrets are uploaded as workflow artifacts. The separate backend-test workflow runs mocked tests without production secrets.

GitHub scheduled workflows are polling, not an immediate or guaranteed delivery mechanism. Runs can be delayed; public-repository schedules may be disabled after 60 days without activity. See [GitHub's schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). The durable database queue survives a missed run.

## Instagram cookies

`INSTAGRAM_COOKIES_B64` is base64 of a Netscape-format Instagram cookies file, matching [yt-dlp's supported cookie-file format](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp).

At download time the backend decodes and validates the file, retains only Instagram-domain cookies, writes a file with owner-only permissions, and passes its path as yt-dlp's `cookiefile`. That directory is deleted after extraction, including failures. It is separate from the audio directory, so fallback audio selection cannot accidentally select a cookie file. Invalid cookie errors do not print cookie values.

Session cookies with expiry zero are supported. Absent or expired cookies allow an unauthenticated public-access attempt; a login/rate-limit failure gives an actionable instruction to refresh the cookie secret and resubmit the Reel. Cookies do not guarantee that Instagram will accept a hosted runner's requests.

The downloaded media directory is also removed on download failure or when processing finishes, including failures before transcription. Missing transcription credentials no longer leave the audio file behind.

## Required configuration

In **GitHub → jeffersonqiu/insta_reels_tools_logger → Settings → Secrets and variables → Actions**, configure these repository secrets:

| Name | Source |
| --- | --- |
| `SUPABASE_URL` | Existing production Supabase URL |
| `SUPABASE_SERVICE_KEY` | Existing backend Supabase service-role key |
| `ASSEMBLYAI_API_KEY` | Existing AssemblyAI key |
| `ANTHROPIC_API_KEY` | Existing Anthropic key |
| `INSTAGRAM_COOKIES_B64` | Existing Railway value, or a refreshed Instagram-only Netscape export |

The first four are required for processing. Cookies are optional for public content but address the known Instagram login problem. Do not paste secret values into chat, commit them, or create a plaintext configuration artifact. Copying existing credentials into GitHub Actions grants that runner access to the production database and paid processing APIs; it requires explicit authorization before browser entry.

## Cutover order

1. Publish the tested branch and check that the backend-test workflow passes.
2. Merge the code with Railway still using its default `PROCESSING_MODE=inline`. Scheduled processing remains disabled until `PROCESSING_WORKER_ENABLED=true` exists. Verify `/health`, `/health/db`, `/api/items`, and `/api/diagnostics/processing` (`mode=inline`).
3. Configure the repository secrets listed above.
4. In **Actions → Process queued Reels → Run workflow**, leave `dry_run=true`. Confirm it succeeds and reports the candidate count. This reads production but incurs no transcription/LLM cost and makes no writes.
5. Set Railway's `PROCESSING_MODE=github_actions` and deploy the configuration change. Verify `GET /api/diagnostics/processing` returns `{"mode":"github_actions"}`. The webhook now only saves the queue.
6. Set the GitHub repository variable `PROCESSING_WORKER_ENABLED=true`. The next scheduled job claims queued work. A manual `dry_run=false` run with `batch_size=1` can verify one deliberately queued Reel sooner.
7. Confirm a deliberately submitted or explicitly retried Reel progresses queued → processing → completed (or failed with an actionable persisted error), and completed work has its knowledge item and expected Tools relationships.

Do not bulk-requeue failed historical videos or run the paid knowledge backfill during cutover. A missing/expired cookie may still require a new Instagram session export from the account owner.

Rollback: set `PROCESSING_WORKER_ENABLED=false`, let any running workflow finish, and set Railway `PROCESSING_MODE=inline`. Stored queued/failed videos and knowledge items remain available. Atomic claims also protect brief overlap during cutover or rollback.

## Local verification

From `backend/`:

```sh
uv run pytest
uv run python scripts/process_queue.py --dry-run
```

The dry run needs Supabase credentials and reads the intended database. Processing mode can be inspected with:

```text
GET https://instareelstoolslogger-production.up.railway.app/api/diagnostics/processing
```

AssemblyAI and the current transcript/caption knowledge extraction are retained. Vision/OCR, local transcription, Library UI, Telegram Q&A, MCP, and Markdown export are separate follow-up work.
