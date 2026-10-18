"""Whole-repository access and bounded natural-language assistant regressions."""
import copy
import json
from types import SimpleNamespace

import pytest
from config import settings
from services import knowledge_qa as qa, telegram_handler as handler
from services.knowledge_repository import load_repository, _rows, RepositoryError
from test_knowledge_items import FakeSupabase
from test_telegram import ITEM, ITEM_ID, env, fake_answer, post, update


def video(key, date='2026-10-01T00:00:00Z', **kwargs):
    return {'id': key, 'instagram_url': f'https://www.instagram.com/reel/{key}/', 'status': 'completed', 'processed_at': date, 'transcript': 'A useful tutorial.', **kwargs}


def tool(key, **kwargs):
    return {'id': key, 'name': key, 'functionality': 'A saved tool.', 'first_seen_date': '2026-09-01', **kwargs}


def test_all_legacy_content_tools_and_notes_visible_without_writes():
    db = FakeSupabase()
    db.tables = {
        'knowledge_items': [{**ITEM, 'video_id': 'new'}],
        'videos': [video('new'), video('old', raw_extraction=[{'name': 'LegacyKit'}], transcript='Exclusive old transcript')],
        'tools': [tool('legacy', name='LegacyKit', source_video_ids=['old']), tool('orphan')],
        'user_interactions': [{'id': 'interaction', 'tool_id': 'legacy', 'status': 'implemented', 'notes': 'Use at work'}],
        'video_tools': [{'video_id': 'old', 'tool_id': 'legacy'}],
    }
    before = copy.deepcopy(db.tables)
    by_id = {row['id']: row for row in load_repository(db)}
    assert len(by_id) == 4 and db.tables == before
    assert by_id['video:old']['transcript'] == 'Exclusive old transcript'
    assert by_id['video:old']['title'] == 'LegacyKit'
    assert by_id['tool:legacy']['status'] == 'implemented'
    assert by_id['tool:legacy']['notes'] == 'Use at work'
    assert by_id['tool:orphan']['source_url'] == ''
    assert by_id[ITEM_ID]['transcript'] == 'A useful tutorial.'


def test_all_tables_page_beyond_supabase_default():
    db = FakeSupabase()
    db.tables['tools'] = [tool(f't{i:04d}') for i in range(1005)]
    db.tables['videos'] = [video(f'v{i:04d}') for i in range(205)]
    db.tables['user_interactions'] = [{'id': f'i{i:04d}', 'tool_id': f't{i:04d}', 'notes': 'late-page-note'} for i in range(1005)]
    db.tables['video_tools'] = [{'video_id': 'v0204', 'tool_id': f't{i:04d}'} for i in range(1005)]
    sources = load_repository(db)
    assert len(sources) == 1210
    assert next(row for row in sources if row['id'] == 'tool:t1004')['notes'] == 'late-page-note'
    assert len(next(row for row in sources if row['id'] == 'video:v0204')['related_tools']) == 1005


def test_nonadvancing_pagination_fails_closed():
    class Stuck:
        def table(self, name): return self
        def select(self, columns): return self
        def order(self, key): return self
        def range(self, start, end): return self
        def execute(self): return SimpleNamespace(data=[{'id': str(i)} for i in range(200)])
    with pytest.raises(RepositoryError, match='did not advance'):
        _rows(Stuck(), 'tools', 'id')


def test_recent_distinct_content_uses_save_not_publication_dates(env):
    env.db.tables['knowledge_items'][0]['video_id'] = 'v1'
    env.db.tables['videos'] = [
        video('v1', '2026-10-03T00:00:00Z', instagram_url=ITEM['source_url'], video_created_at='2020-01-01'),
        video('duplicate', '2026-10-04T00:00:00Z', instagram_url=ITEM['source_url'] + '?igsh=tracking', transcript='Other saved text'),
        video('v2', '2026-10-02T00:00:00Z', caption='Second saved content'),
    ]
    env.db.tables['tools'] = [tool('newest-tool', first_seen_date='2026-10-17')]
    result, selected = qa._read_tool('list_library', {'kind': 'content', 'limit': 3}, qa._all_items())
    assert [row['id'] for row in selected] == [ITEM_ID, 'video:v2']
    assert result['total_sources'] == 2 and 'Other saved text' in selected[0]['transcript']
    assert selected[0]['saved_at'] == '2026-10-03T00:00:00Z'
    assert selected[0]['published_on'] == '2020-01-01'
    assert 'Second saved content' in qa.recent_items() and 'newest-tool' not in qa.recent_items()


def test_exact_natural_question_has_full_catalogue_without_keyword_gate(env, monkeypatch):
    env.db.tables['tools'] = [tool('older', name='OlderSandbox', functionality='Isolate untrusted generated code')]
    calls, _ = fake_answer(monkeypatch, {'can_answer': True, 'recommendations': [{'source_id': ITEM_ID, 'takeaway': 'A saved canvas.', 'why': 'Try visual workflows.', 'next_step': 'Build a small pipeline.'}]})
    answer = qa.answer_question("what's the latest 3 content that worth I spend my time on")
    payload = json.loads(calls[0]['messages'][0]['content'])
    assert {row['id'] for row in payload['catalogue']} == {ITEM_ID, 'tool:older'}
    assert payload['catalogue_complete'] is True and 'Sources:' in answer
    assert 'publication' in calls[0]['system'] and 'not_interested' in calls[0]['system']


def test_search_includes_transcript_tail_and_notes(env):
    env.db.tables['videos'] = [video('older', transcript='x' * 15000 + ' singlediscovery')]
    env.db.tables['tools'] = [tool('noted')]
    env.db.tables['user_interactions'] = [{'id': 'i', 'tool_id': 'noted', 'status': 'to_explore', 'notes': 'specialnote'}]
    sources = qa._all_items()
    assert [row['id'] for row in qa.retrieve('singlediscovery', sources)] == ['video:older']
    assert [row['id'] for row in qa.retrieve('specialnote', sources)] == ['tool:noted']


def scripted_model(monkeypatch, steps):
    calls = []
    def create(**kwargs):
        calls.append(copy.deepcopy(kwargs))
        name, value = steps[len(calls) - 1]
        return SimpleNamespace(content=[SimpleNamespace(type='tool_use', id=f'call-{len(calls)}', name=name, input=value)], stop_reason='tool_use')
    monkeypatch.setattr(qa, 'Anthropic', lambda **kwargs: SimpleNamespace(messages=SimpleNamespace(create=create)))
    monkeypatch.setattr(settings, 'anthropic_api_key', 'fake')
    return calls


def test_large_repository_searches_and_reads_old_sources(env, monkeypatch):
    env.db.tables['tools'] = [tool(f'old-{i:04d}', functionality='a' * 600) for i in range(250)]
    env.db.tables['tools'][0]['functionality'] = 'exclusiveoldconcept'
    calls = scripted_model(monkeypatch, [
        ('search_library', {'query': 'exclusiveoldconcept'}),
        ('read_sources', {'source_ids': ['tool:old-0000']}),
        ('answer_from_library', {'can_answer': True, 'answer': 'Here is the older saved concept.', 'source_ids': ['tool:old-0000']}),
    ])
    assert 'older saved concept' in qa.answer_question('What did I save about exclusiveoldconcept?')
    first = json.loads(calls[0]['messages'][0]['content'])
    assert first['catalogue_complete'] is False and first['catalogue'] == []
    assert all(tool['name'] != 'answer_from_library' for tool in calls[0]['tools'])
    assert len(calls) == qa.MAX_CALLS
    assert calls[-1]['tool_choice'] == {'type': 'tool', 'name': 'answer_from_library'}
    results = [part for message in calls[-1]['messages'] if isinstance(message['content'], list) for part in message['content'] if part['type'] == 'tool_result']
    assert json.loads(results[0]['content'])['searched_source_count'] == 251


def test_unseen_sources_cannot_be_cited(env, monkeypatch):
    monkeypatch.setattr(qa, 'CATALOG_LIMIT', 1)
    scripted_model(monkeypatch, [('answer_from_library', {'can_answer': True, 'answer': 'Unsupported', 'source_ids': [ITEM_ID]})])
    with pytest.raises(qa.AnswerFormatError, match='Unsupported'):
        qa.answer_question('OpenFlow')


def test_fenced_json_regression_accepted_without_second_paid_call(env, monkeypatch):
    calls, _ = fake_answer(monkeypatch, '```json\n' + json.dumps({'can_answer': True, 'answer': 'A saved canvas.', 'source_ids': [ITEM_ID]}) + '\n```')
    assert 'A saved canvas.' in qa.answer_question('OpenFlow') and len(calls) == 1


def test_natural_question_webhook_completes_with_sources_and_duplicate_cost_is_zero(env, monkeypatch):
    monkeypatch.setattr(handler, 'answer_question', qa.answer_question)
    calls, _ = fake_answer(monkeypatch, '```json\n' + json.dumps({'can_answer': True, 'recommendations': [{'source_id': ITEM_ID, 'takeaway': 'A saved canvas.', 'why': 'Try visual workflows.', 'next_step': 'Build a small pipeline.'}]}) + '\n```')
    body = update("what's the latest 3 content that worth I spend my time on")
    assert post(env, body).json() == {'status': 'accepted'}
    assert env.db.tables['telegram_updates'][0]['status'] == 'completed'
    assert 'Sources:' in env.sent[0][1] and 'saved canvas' in env.sent[0][1]
    assert post(env, body).json() == {'status': 'duplicate'}
    assert len(calls) == 1 and len(env.sent) == 1


def test_read_loop_cannot_exceed_three_model_calls(env, monkeypatch):
    calls = scripted_model(monkeypatch, [('list_library', {'kind': 'content', 'limit': 3})] * 3)
    with pytest.raises(qa.AnswerFormatError, match='Unexpected'):
        qa.answer_question('What should I explore?')
    assert len(calls) == 3 and calls[-1]['tools'] == [qa.ANSWER_TOOL]


def test_recent_recommendations_use_server_dates_titles_and_chronological_order():
    sources = {
        'older': {**ITEM, 'kind': 'video', 'saved_at': '2026-03-27T00:00:00Z', 'title': 'Older saved content'},
        'newer': {**ITEM, 'kind': 'video', 'saved_at': '2026-03-28T00:00:00Z', 'title': 'Newer saved content'},
    }
    recs = [{'source_id': key, 'takeaway': 'A useful pattern.', 'why': 'Could help.', 'next_step': 'Try a small example.'} for key in ['older', 'newer']]
    parsed = qa.GroundedAnswer(can_answer=True, answer='Wrong invented chronological header', recommendations=recs)
    answer = qa._render_answer(parsed, sources, recent=True)
    assert answer.index('1. Newer saved content') < answer.index('2. Older saved content')
    assert 'Saved: 2026-03-28' in answer and 'Saved: 2026-03-27' in answer
    assert 'invented' not in answer
    assert answer.index('[1] Newer saved content') < answer.index('[2] Older saved content')


def test_recent_question_requires_structured_choices_and_verified_ids(env, monkeypatch):
    fake_answer(monkeypatch, {'can_answer': True, 'answer': 'A date-ordered list.', 'source_ids': [ITEM_ID]})
    with pytest.raises(qa.AnswerFormatError, match='incomplete'):
        qa.answer_question('What are the latest three content items worth my time?')
    parsed = qa.GroundedAnswer(can_answer=True, recommendations=[{'source_id': 'invented', 'takeaway': 'x', 'why': 'x', 'next_step': 'x'}])
    with pytest.raises(qa.AnswerFormatError, match='Unsupported'):
        qa._render_answer(parsed, {}, recent=True)


def test_recent_question_can_abstain_without_fabricating_choices(env, monkeypatch):
    calls, _ = fake_answer(monkeypatch, {'can_answer': False, 'recommendations': []})
    assert qa.answer_question('Latest content about quantumgravity?') == qa.NO_ANSWER
    schema = next(tool for tool in calls[0]['tools'] if tool['name'] == 'answer_from_library')['input_schema']
    assert 'recommendations' in schema['required']
    assert schema['properties']['recommendations'].get('minItems', 0) == 0


def test_context_budget_and_transcript_cursor():
    source = {**ITEM, 'kind': 'item', 'transcript': 'x' * 20000, 'caption': 'y' * 20000, 'related_tools': [{'name': str(i), 'notes': 'z' * 20000} for i in range(100)]}
    context = qa._context_item(source, budget=2800, transcript_offset=6000)
    assert len(json.dumps(context, ensure_ascii=False)) < 3000
    assert context['detail_truncated'] is True
    assert context['excerpt_next_offset'] == 6000 + len(context['transcript_excerpt'])
    assert context['transcript_length'] == 20000


@pytest.mark.parametrize('name,arguments', [
    ('search_library', {'query': ''}), ('list_library', {'kind': {}, 'limit': 3}),
    ('list_library', {'kind': 'all', 'limit': True}), ('list_library', {'kind': 'all', 'limit': 9}),
    ('read_sources', {'source_ids': ['made-up']}), ('read_sources', {'source_ids': [None]}),
    ('execute_sql', {'query': 'DELETE FROM tools'}),
])
def test_tools_read_only_and_validate_untrusted_arguments(name, arguments):
    response, selected = qa._read_tool(name, arguments, [{**ITEM, 'kind': 'item'}])
    assert not selected and (response.get('error') or response.get('missing_source_count') == 1)


def test_provider_failure_sanitized_without_retry(env, monkeypatch):
    calls = []
    def fail(**kwargs):
        calls.append(kwargs)
        raise RuntimeError('credential-private-sentinel')
    monkeypatch.setattr(qa, 'Anthropic', lambda **kwargs: SimpleNamespace(messages=SimpleNamespace(create=fail)))
    monkeypatch.setattr(settings, 'anthropic_api_key', 'fake')
    with pytest.raises(qa.AnswerProviderError) as error:
        qa.answer_question('OpenFlow')
    assert 'sentinel' not in str(error.value) and len(calls) == 1


def test_insufficient_credits_classified_without_exposing_provider_payload(env, monkeypatch):
    def fail(**kwargs):
        error = RuntimeError('private-provider-sentinel')
        error.body = {'error': {'message': 'Your credit balance is too low to access the Anthropic API.'}}
        raise error
    monkeypatch.setattr(qa, 'Anthropic', lambda **kwargs: SimpleNamespace(messages=SimpleNamespace(create=fail)))
    monkeypatch.setattr(settings, 'anthropic_api_key', 'fake')
    with pytest.raises(qa.AnswerCreditsError) as error:
        qa.answer_question('OpenFlow')
    assert str(error.value) == qa.NO_CREDITS and 'sentinel' not in str(error.value)


def test_credit_failure_explained_in_telegram_without_retry_or_secret_echo(env, monkeypatch):
    def fail(question):
        raise qa.AnswerCreditsError('private-provider-sentinel')
    monkeypatch.setattr(handler, 'answer_question', fail)
    assert post(env, update('What should I learn next?')).status_code == 200
    assert env.sent[0][1] == qa.NO_CREDITS and 'sentinel' not in env.sent[0][1]
    assert env.db.tables['telegram_updates'][0]['error_type'] == 'AnswerCreditsError'
    assert post(env, update('What should I learn next?')).json() == {'status': 'duplicate'}
    assert len(env.sent) == 1


def test_incomplete_answer_fails_closed(env, monkeypatch):
    monkeypatch.setattr(settings, 'anthropic_api_key', 'fake')
    monkeypatch.setattr(qa, 'Anthropic', lambda **kwargs: SimpleNamespace(messages=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(content=[], stop_reason='max_tokens'))))
    with pytest.raises(qa.AnswerFormatError, match='incomplete'):
        qa.answer_question('OpenFlow')


def test_links_use_existing_routes(env):
    assert qa.source_link({'id': 'tool:1', 'kind': 'tool', 'title': 'Legacy Tool', 'video_id': '1'}) == 'https://library.example/videos/1'
    assert qa.source_link({'id': 'tool:2', 'kind': 'tool', 'title': 'Orphan Tool'}) == ''
    assert qa.source_link({'id': 'video:1', 'video_id': '1', 'kind': 'video'}) == 'https://library.example/videos/1'
