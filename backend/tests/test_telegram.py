"""Private Telegram authorization, deduplication, setup and grounded answers."""
import asyncio
import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import Settings, settings
from main import app
from routers import telegram as router
from services import knowledge_qa as qa, telegram_api, telegram_handler as handler
from test_knowledge_items import FakeSupabase

ITEM_ID = '20000000-0000-0000-0000-000000000001'
ITEM = {'id': ITEM_ID, 'title': 'OpenFlow visual agent canvas', 'summary': 'Wire planner and coder roles together.', 'key_ideas': ['Parallel agents on real files'], 'concepts': ['Orchestration'], 'action_items': [], 'tags': ['agents'], 'repositories': [], 'raw_extraction': {'tools': []}, 'source_url': 'https://www.instagram.com/reel/ABC/', 'created_at': '2026-10-01T00:00:00Z'}


def update(text='/ask What is OpenFlow?', user=123, chat=None, kind='private', number=1):
    return {'update_id': number, 'message': {'from': {'id': user, 'is_bot': False}, 'chat': {'id': chat if chat is not None else user, 'type': kind}, 'text': text}}


@pytest.fixture
def env(monkeypatch):
    db, sent, questions = FakeSupabase(), [], []
    db.tables['knowledge_items'] = [dict(ITEM)]
    for name, value in {'webhook_secret': 'admin-test-secret', 'telegram_bot_token': '123:test-bot-credential', 'telegram_allowed_user_ids': '123', 'public_app_url': 'https://library.example', 'processing_mode': 'github_actions'}.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(handler, 'get_supabase', lambda: db)
    monkeypatch.setattr(qa, 'get_supabase', lambda: db)
    monkeypatch.setattr('routers.webhook.get_supabase', lambda: db)
    async def reply(chat_id, text): sent.append((chat_id, text))
    def answer(question):
        questions.append(question)
        return 'Grounded answer with sources.'
    monkeypatch.setattr(handler, 'reply', reply)
    monkeypatch.setattr(handler, 'answer_question', answer)
    return SimpleNamespace(db=db, sent=sent, questions=questions, client=TestClient(app))


def post(env, body, secret=None):
    return env.client.post('/api/webhook/telegram', json=body, headers={'X-Telegram-Bot-Api-Secret-Token': secret if secret is not None else telegram_api.webhook_token()})


def test_authentication_precedes_storage_or_paid_calls(env):
    assert post(env, update(), 'wrong').status_code == 401
    assert env.client.post('/api/webhook/telegram', content='invalid').status_code == 401
    assert env.questions == env.sent == [] and 'telegram_updates' not in env.db.tables


@pytest.mark.parametrize('body', [update(user=456), update(kind='group', chat=-1), update(chat=456), {'update_id': 1, 'edited_message': {}}])
def test_unauthorized_or_unsupported_updates_ignored(env, body):
    assert post(env, body).json() == {'status': 'ignored'}
    assert env.questions == env.sent == [] and 'telegram_updates' not in env.db.tables


def test_empty_allowlist_only_reveals_requesters_own_id(env, monkeypatch):
    monkeypatch.setattr(settings, 'telegram_allowed_user_ids', '')
    assert post(env, update()).json() == {'status': 'ignored'}
    assert post(env, update('/start', user=456)).json() == {'status': 'accepted'}
    assert env.sent[0][0] == 456 and '456' in env.sent[0][1]
    assert 'TELEGRAM_ALLOWED_USER_IDS' in env.sent[0][1]
    assert not env.questions and 'telegram_updates' not in env.db.tables


def test_duplicate_delivery_never_repeats_paid_answer(env):
    assert post(env, update()).status_code == 200
    assert post(env, update()).json() == {'status': 'duplicate'}
    assert env.questions == ['What is OpenFlow?'] and len(env.sent) == 1
    event = env.db.tables['telegram_updates'][0]
    assert event['status'] == 'completed' and 'OpenFlow' not in json.dumps(event)
    assert set(event) == {'id', 'update_id', 'status', 'error_type', 'finished_at'}


def test_claim_failure_requests_redelivery_without_work(env, monkeypatch):
    def fail(_): raise RuntimeError('credential-sentinel')
    monkeypatch.setattr(router, 'claim_update', fail)
    response = post(env, update())
    assert response.status_code == 503 and 'sentinel' not in response.text
    assert not env.questions and not env.sent


def test_failed_answer_does_not_leak_error_or_retry_paid_work(env, monkeypatch, caplog):
    def fail(_): raise RuntimeError('private-provider-sentinel')
    monkeypatch.setattr(handler, 'answer_question', fail)
    assert post(env, update()).status_code == 200
    assert env.db.tables['telegram_updates'][0]['status'] == 'failed'
    assert env.db.tables['telegram_updates'][0]['error_type'] == 'RuntimeError'
    assert 'private-provider-sentinel' not in caplog.text + json.dumps(env.sent)
    assert 'new message' in env.sent[0][1]
    assert post(env, update()).json() == {'status': 'duplicate'}


def test_reels_use_existing_durable_ingestion(env):
    for number in [1, 2]:
        assert post(env, update('https://www.instagram.com/reel/ABC/?igsh=tracking', number=number)).status_code == 200
    assert len(env.db.tables['videos']) == 1 and env.db.tables['videos'][0]['status'] == 'queued'
    assert not env.questions and 'already saved' in env.sent[1][1]


@pytest.mark.parametrize('text', ['/ask', '/ask ' + 'a' * 1501, '/help', '/recent', '/unknown'])
def test_non_questions_do_not_call_llm(env, text):
    assert post(env, update(text)).status_code == 200
    assert not env.questions and env.sent


def test_malformed_large_and_unconfigured_updates(env, monkeypatch):
    assert post(env, {'update_id': True}).status_code == 422
    assert env.client.post('/api/webhook/telegram', content='x' * 131073, headers={'X-Telegram-Bot-Api-Secret-Token': telegram_api.webhook_token()}).status_code == 413
    monkeypatch.setattr(settings, 'telegram_bot_token', '')
    assert post(env, update()).status_code == 503


@pytest.mark.parametrize('value', ['123,0', '-1', '123,', 'alice', '[123]', '１２３'])
def test_invalid_allowed_users_rejected(value):
    with pytest.raises(ValidationError): Settings(_env_file=None, telegram_allowed_user_ids=value)


def test_valid_user_configuration():
    assert Settings(_env_file=None, telegram_allowed_user_ids=' 123, 456 ').telegram_allowed_user_ids == '123,456'


def setup(env, **kwargs):
    return env.client.post('/api/telegram/setup', json={'secret': settings.webhook_secret, 'expected_username': 'jeqiu_insta_reel_bot', **kwargs})


def setup_requests(monkeypatch, username='jeqiu_insta_reel_bot'):
    calls = []
    async def request(method, payload=None):
        calls.append((method, payload))
        if method == 'getMe': return {'username': username}
        if method == 'setWebhook': return True
        return {'url': 'https://api.example/api/webhook/telegram', 'pending_update_count': 0}
    monkeypatch.setattr(router, 'bot_request', request)
    return calls


def test_setup_auth_missing_token_and_read_only_inspection(env, monkeypatch):
    calls = setup_requests(monkeypatch)
    assert setup(env, secret='wrong').status_code == 401 and not calls
    response = setup(env)
    assert response.status_code == 200
    assert [method for method, _ in calls] == ['getMe', 'getWebhookInfo']
    assert settings.telegram_bot_token not in response.text and settings.webhook_secret not in response.text
    assert response.json()['allowed_user_count'] == 1
    monkeypatch.setattr(settings, 'telegram_bot_token', '')
    assert setup(env).status_code == 503


def test_registration_preserves_pending_updates_and_derives_secret(env, monkeypatch):
    calls = setup_requests(monkeypatch)
    response = setup(env, operation='register', public_api_url='https://api.example')
    assert response.json()['registered_expected_url'] is True
    payload = next(data for method, data in calls if method == 'setWebhook')
    assert payload['secret_token'] == telegram_api.webhook_token() != settings.webhook_secret
    assert payload['url'] == 'https://api.example/api/webhook/telegram'
    assert payload['allowed_updates'] == ['message'] and payload['max_connections'] == 1
    assert 'drop_pending_updates' not in payload


def test_wrong_bot_never_changes_webhook(env, monkeypatch):
    calls = setup_requests(monkeypatch, 'other_bot')
    assert setup(env, operation='register', public_api_url='https://api.example').status_code == 400
    assert [method for method, _ in calls] == ['getMe']


@pytest.mark.parametrize('url', ['http://api.example', 'https://user:password@api.example', 'https://api.example/other', 'https://api.example/?x=1'])
def test_invalid_setup_origins(env, url):
    assert setup(env, operation='register', public_api_url=url).status_code == 400


def fake_answer(monkeypatch, payload):
    calls, options = [], []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(content=[SimpleNamespace(text=payload if isinstance(payload, str) else json.dumps(payload))])
    def client(**kwargs):
        options.append(kwargs)
        return SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setattr(qa, 'Anthropic', client)
    monkeypatch.setattr(settings, 'anthropic_api_key', 'test-key')
    return calls, options


def test_answer_has_verified_sources_and_one_bounded_call(env, monkeypatch):
    calls, options = fake_answer(monkeypatch, {'can_answer': True, 'answer': 'It connects AI roles.', 'source_ids': [ITEM_ID]})
    result = qa.answer_question('What is OpenFlow?')
    assert 'It connects AI roles.' in result and 'https://library.example/items/' + ITEM_ID in result
    assert len(calls) == 1 and calls[0]['max_tokens'] == 900 and calls[0]['model'] == settings.anthropic_model
    assert options[0]['max_retries'] == 0 and options[0]['timeout'] == 30
    assert len(calls[0]['messages'][0]['content']) < 20000
    assert 'untrusted data' in calls[0]['system']


def test_no_relevant_sources_never_calls_llm(env, monkeypatch):
    monkeypatch.setattr(qa, 'Anthropic', lambda **kwargs: pytest.fail('No relevant sources must not incur an LLM call'))
    assert qa.answer_question('quantumgravity') == qa.NO_ANSWER
    env.db.tables['knowledge_items'] = []
    assert qa.answer_question('OpenFlow') == qa.NO_ANSWER


@pytest.mark.parametrize('payload', ['private-output-sentinel', {'can_answer': True, 'answer': 'Unsupported', 'source_ids': ['invented']}, {'can_answer': True, 'answer': 'Unsupported', 'source_ids': []}])
def test_unverifiable_answers_do_not_expose_raw_output(env, monkeypatch, payload):
    fake_answer(monkeypatch, payload)
    with pytest.raises(qa.AnswerError) as error: qa.answer_question('OpenFlow')
    assert 'private-output-sentinel' not in str(error.value)


def test_model_can_abstain_and_cannot_create_urls(env, monkeypatch):
    fake_answer(monkeypatch, {'can_answer': False, 'answer': 'Untrusted', 'source_ids': []})
    assert qa.answer_question('OpenFlow') == qa.NO_ANSWER
    fake_answer(monkeypatch, {'can_answer': True, 'answer': 'Saved canvas https://invented.example', 'source_ids': [ITEM_ID]})
    assert 'invented.example' not in qa.answer_question('OpenFlow')


def test_unsafe_source_links_not_rendered(env, monkeypatch):
    monkeypatch.setattr(settings, 'public_app_url', 'javascript:alert(1)')
    assert qa.source_link({**ITEM, 'source_url': 'javascript:alert(1)'}) == ''
    assert qa.source_link(ITEM) == ITEM['source_url']


def test_http_logs_redact_bot_token(env, caplog):
    with caplog.at_level(logging.INFO, logger='httpx'):
        logging.getLogger('httpx').info('POST %s', 'https://api.telegram.org/bot' + settings.telegram_bot_token + '/sendMessage')
    assert settings.telegram_bot_token not in caplog.text and '[redacted]' in caplog.text


def test_unicode_replies_split_without_loss(env, monkeypatch):
    sent = []
    async def request(method, payload): sent.append(payload)
    monkeypatch.setattr(telegram_api, 'bot_request', request)
    text = '🙂' * 2500 + '\nSources:\nhttps://example.com'
    asyncio.run(telegram_api.reply(123, text))
    assert ''.join(payload['text'] for payload in sent) == text
    assert all(len(payload['text'].encode('utf-16-le')) // 2 <= 4000 for payload in sent)
    assert all('parse_mode' not in payload and payload['link_preview_options']['is_disabled'] for payload in sent)
