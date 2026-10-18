"""Import source-reviewed knowledge without invoking paid extraction or changing tools."""
import datetime as dt
import hashlib
import json

from models.schemas import KnowledgeExtraction
from services.ingestion import canonicalize_reel_url
from services.knowledge_repository import _rows, VIDEO_FIELDS


def source_digest(video):
    source = {key:video.get(key) for key in ['transcript','caption']}
    return hashlib.sha256(json.dumps(source, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def import_reviewed(db, entries, *, apply=False):
    videos = {row['id']:row for row in _rows(db, 'videos', VIDEO_FIELDS)}
    existing = {row['video_id'] for row in _rows(db, 'knowledge_items', 'id,video_id')}
    prepared, seen, skipped = [], set(), []
    for entry in entries:
        video_id = entry['video_id']
        if video_id in seen:
            raise ValueError('Duplicate video in reviewed input.')
        seen.add(video_id)
        if video_id in existing:
            skipped.append(video_id)
            continue
        video = videos.get(video_id)
        if not video or video.get('status') != 'completed' or not (video.get('transcript') or '').strip():
            raise ValueError('Reviewed imports require a completed video with a stored transcript.')
        if source_digest(video) != entry.get('source_sha256'):
            raise ValueError('Stored source changed after review; review it again before importing.')
        extraction = KnowledgeExtraction.model_validate(entry['knowledge']).model_dump()
        if not extraction['title'].strip() or not extraction['summary'].strip():
            raise ValueError('Reviewed entries need a title and summary.')
        reasons = entry.get('review_reasons', [])
        if not isinstance(reasons, list) or not all(isinstance(reason, str) for reason in reasons):
            raise ValueError('Review reasons must be a list of text.')
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        raw = {**extraction, 'curation':{'method':'reviewed_stored_transcript', 'reviewed_at':now, 'needs_review':bool(reasons), 'review_reasons':reasons, 'source_sha256':entry['source_sha256']}}
        row = {key:extraction[key] for key in ['title','summary','key_ideas','repositories','concepts','action_items','tags']}
        row.update(video_id=video_id, source_type='instagram_reel', source_url=canonicalize_reel_url(video.get('canonical_url') or video['instagram_url']), raw_extraction=raw, created_at=video.get('processed_at') or now, updated_at=now)
        prepared.append(row)
    # Validate the whole batch before the first write; conflict-ignore protects
    # concurrent processing. Re-running a partially completed import is safe.
    inserted = []
    if apply:
        for row in prepared:
            result = db.table('knowledge_items').upsert(row, on_conflict='video_id', ignore_duplicates=True).execute().data
            inserted.extend(result or [])
    return {'planned_count':len(prepared), 'inserted_count':len(inserted), 'skipped_video_ids':skipped,
            'items':[{'video_id':row['video_id'],'title':row['title'],'review_reasons':row['raw_extraction']['curation']['review_reasons']} for row in prepared]}
