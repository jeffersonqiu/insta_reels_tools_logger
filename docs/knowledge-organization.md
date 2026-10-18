# Knowledge shelves and weekly review

Sources remain durable knowledge items, with their original Reel, transcript, caption, save date and extracted tools. Topics organize items; tags describe finer detail. A source can appear under several topics. Topic guides collect ideas and proposed actions with links to their source entries. They are reading guides, not independently verified research summaries.

## Current shelves

- Agents & orchestration
- Coding workflows & skills
- Integrations & interfaces
- Production reliability
- Search & multimodal

Two catch-all queues always remain visible, including when empty:

- **Inbox**: no clear topic match yet.
- **Needs review**: source limitations or unresolved questions, even when the topic is known.

New items are classified on read using the versioned `backend/services/topic_catalog.json`. This requires no paid AI call and no new database migration. Unknown material goes to Inbox. The rules use tags and source summaries/ideas; they are deliberately a first pass. Reviewed assignments can override them by stable video ID. Topic membership is a view of the saved knowledge, so reorganizing shelves does not duplicate or move source records.

The catalogue stores stable topic IDs, descriptions, a reading guide, matching vocabulary and optional reviewed per-video assignments. Raise its version when changing organization. Preserve topic IDs and existing source links. No destructive merge is needed to reconsider the structure of this small library.

## Weekly review procedure

1. Read this document and the current catalogue, check the repository state and production availability, and preserve any in-progress work. Use an isolated branch/checkout when needed.
2. Run `uv run python scripts/review_knowledge.py --env-file PATH --output PATH` from `backend/`, using the existing backend configuration privately. The report contains topic sizes, catch-all queues, repeated unmatched tags, missing knowledge items and unfinished videos. It does not call Anthropic or send Telegram messages.
3. Inspect source summaries, tags, ideas and, where necessary, stored transcripts/captions. Review every catch-all item; process at most 20 source records requiring manual enrichment per run. Assign clear Inbox items to existing topics. If the evidence is ambiguous, keep the item in Inbox and record why. Keep unresolved source problems in Needs review; clearing a flag requires actual supporting evidence, not the desire to empty the queue.
4. Review whether shelves still make sense: vague or oversized topics, overlap, repeated uncategorized themes, empty shelves and topics worth splitting or combining. Prefer a few useful shelves over a new category for each source. Three related unmatched items are a signal to consider a new topic, not an automatic rule. Any changes should preserve stable IDs and links and be recorded in a dated review note.
5. For missing historical knowledge, source-review the existing transcript and extraction, validate a source fingerprint and use `import_reviewed_knowledge.py` in dry-run mode first. Apply only missing rows; preserve original save dates, source records, tool records, notes and statuses. Do not invoke paid extraction, transcription or downloads as part of this organization review.
6. Add reviewed topic overrides or adjust matching rules when supported. Verify the resulting topic memberships and counts, then run full backend tests. Run frontend tests, lint and build if UI files change. Publish through a feature branch; merge and verify deployment only when checks pass and required migrations are already applied. Do not force-push over another change.
7. Save a short dated note under `docs/knowledge-reviews/`: source IDs reviewed, changes, unresolved reasons, structural decisions and verification. Record unchanged/blocked outcomes without inventing work. Notify in the existing chat only for meaningful changes, failures or required owner action. Do not send Telegram, email or other external messages.

The review agent uses reasoning in this Codex chat rather than the app's Anthropic API. Library browsing and catch-all classification continue to work while Anthropic API credits are unavailable. Telegram's AI answers still require its configured provider to have usable credits.

## Reviewed imports

`backend/scripts/import_reviewed_knowledge.py --input FILE --env-file PATH` validates all entries without writing. Add `--apply` only after source review. The JSON entries contain `video_id`, `source_sha256`, a `KnowledgeExtraction` object and optional `review_reasons`. Source fingerprints cover the stored transcript and caption. Changed sources, incomplete import data and duplicate input IDs fail before the first write. Conflict-ignore insertion and skipping existing items make partial-run recovery idempotent. This import never calls an AI provider and never changes existing Tools behavior.
