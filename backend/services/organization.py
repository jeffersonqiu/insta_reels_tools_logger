"""Versioned topic shelves and catch-all queues, computed without paid AI calls."""
import datetime as dt
import json
import re
from collections import Counter
from pathlib import Path

CATALOG_PATH = Path(__file__).with_name('topic_catalog.json')
CATCH_ALL = [
    {'id': 'inbox', 'name': 'Inbox', 'description': 'Saved knowledge awaiting a clear topic. Reviewed every week.', 'guide': 'Keep uncertain items visible here until their topic is clear.', 'catch_all': True},
    {'id': 'needs-review', 'name': 'Needs review', 'description': 'Sources with incomplete material, uncertain claims or unresolved questions.', 'guide': 'Check the reason attached to each item. A weekly review keeps unresolved questions visible; it does not turn uncertain claims into verified facts.', 'catch_all': True},
]


def load_catalog(path=CATALOG_PATH):
    data = json.loads(Path(path).read_text())
    ids = [topic['id'] for topic in data['topics']]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', key) or key in {'inbox', 'needs-review'} for key in ids):
        raise ValueError('Topic IDs must be unique stable slugs.')
    for override in data.get('overrides', {}).values():
        if any(key not in ids for key in override.get('topic_ids', [])):
            raise ValueError('An override references an unknown topic.')
        if not all(isinstance(reason, str) for reason in override.get('review_reasons', [])):
            raise ValueError('Review reasons must be text.')
    return data


def _contains(text, phrase):
    return bool(re.search(r'(?<!\w)' + re.escape(phrase.casefold()) + r'(?!\w)', text))


def annotate_item(item, catalog=None):
    catalog = catalog or load_catalog()
    lookup = {topic['id']: topic for topic in catalog['topics'] + CATCH_ALL}
    override = catalog.get('overrides', {}).get(item.get('video_id'), {})
    raw = item.get('raw_extraction') if isinstance(item.get('raw_extraction'), dict) else {}
    curation = raw.get('curation') or {}
    reasons = override.get('review_reasons', curation.get('review_reasons', []))
    if curation.get('needs_review') and 'review_reasons' not in override and not reasons:
        reasons = ['This source needs a review.']
    if 'topic_ids' in override:
        ids = list(dict.fromkeys(override['topic_ids']))
        method = 'reviewed assignment'
    else:
        tags = {str(tag).casefold() for tag in item.get('tags') or []}
        title = (item.get('title') or '').casefold()
        body = json.dumps({key:item.get(key) for key in ['summary','concepts','key_ideas']}, ensure_ascii=False).casefold()
        ranked = []
        for index, topic in enumerate(catalog['topics']):
            score = 4 * sum(tag.casefold() in tags for tag in topic['match_tags'])
            score += sum(3 * _contains(title, phrase) + _contains(body, phrase) for phrase in topic['match_phrases'])
            if score >= 3:
                ranked.append((-score, index, topic['id']))
        ids = [key for _, _, key in sorted(ranked)[:3]]
        method = 'topic rules'
    if not ids:
        ids = ['inbox']
    if reasons:
        ids.append('needs-review')
    return {**item, 'topic_ids': ids, 'topics': [{'id':key, 'name':lookup[key]['name']} for key in ids],
            'review_reasons': reasons, 'organization_method': method, 'organization_version': catalog['version']}


def organize_items(items, catalog=None):
    catalog = catalog or load_catalog()
    return [annotate_item(item, catalog) for item in items]


def topic_summary(items, catalog=None):
    catalog = catalog or load_catalog()
    organized = organize_items(items, catalog)
    counts = Counter(key for item in organized for key in item['topic_ids'])
    return [{key:topic.get(key) for key in ['id','name','description','guide']} | {'count':counts[topic['id']], 'catch_all':topic.get('catch_all', False)}
            for topic in catalog['topics'] + CATCH_ALL]


def topic_detail(topic_id, items, catalog=None):
    catalog = catalog or load_catalog()
    topic = next((row for row in topic_summary(items, catalog) if row['id'] == topic_id), None)
    if topic is None:
        return None
    selected = [item for item in organize_items(items, catalog) if topic_id in item['topic_ids']]
    selected.sort(key=lambda item:(item.get('created_at') or '',item['id']), reverse=True)
    def collect(field):
        groups = {}
        for item in selected:
            for text in item.get(field) or []:
                normalized = str(text).strip().casefold()
                if not normalized:
                    continue
                row = groups.setdefault(normalized, {'text':text, 'sources':[]})
                source = {'id':item['id'], 'title':item.get('title')}
                if source not in row['sources']:
                    row['sources'].append(source)
        return list(groups.values())
    return {**topic, 'items':selected, 'ideas':collect('key_ideas'), 'actions':collect('action_items'), 'concepts':collect('concepts')}


def review_snapshot(items, catalog=None, now=None):
    catalog = catalog or load_catalog()
    now = now or dt.datetime.now(dt.timezone.utc)
    organized = organize_items(items, catalog)
    summary = topic_summary(items, catalog)
    queues = [item for item in organized if {'inbox','needs-review'} & set(item['topic_ids'])]
    suggestions = []
    for topic in summary:
        if not topic['catch_all'] and topic['count'] == 0:
            suggestions.append({'kind':'empty_topic', 'topic_id':topic['id'], 'suggestion':'Check whether this shelf should stay visible; preserve its stable ID.'})
        if not topic['catch_all'] and topic['count'] >= 20 and topic['count'] > len(items) * .6:
            suggestions.append({'kind':'large_topic', 'topic_id':topic['id'], 'suggestion':'Inspect whether distinct subtopics would make this shelf easier to browse.'})
    unmatched_tags = Counter(tag for item in organized if 'inbox' in item['topic_ids'] for tag in set(item.get('tags') or []))
    return {'reviewed_at':now.isoformat(), 'catalog_version':catalog['version'], 'item_count':len(items), 'topics':summary,
            'queues':[{'id':item['id'],'video_id':item.get('video_id'),'title':item.get('title'),'topic_ids':item['topic_ids'],'review_reasons':item['review_reasons']} for item in queues],
            'possible_new_topics':[{'tag':tag,'count':count} for tag,count in unmatched_tags.most_common() if count >= 3], 'structure_suggestions':suggestions}
