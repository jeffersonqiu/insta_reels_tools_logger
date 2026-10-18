import copy
import json
import pytest
from fastapi.testclient import TestClient
from main import app
from routers import items as items_router, topics as topics_router
from services.organization import annotate_item, load_catalog, review_snapshot, topic_detail, topic_summary
from services.reviewed_import import import_reviewed, source_digest
from services.knowledge_repository import load_repository
from test_knowledge_items import FakeSupabase

ITEM={'id':'20000000-0000-0000-0000-000000000001','video_id':'v1','title':'Parallel agents','summary':'Coordinate roles.','tags':['agents'],'key_ideas':['Split roles'],'action_items':['Try a small workflow'],'concepts':['Shared memory'],'created_at':'2026-03-01T00:00:00Z','raw_extraction':{}}


def test_unknown_topic_defaults_to_inbox_and_catchalls_stay_visible():
    item=annotate_item({**ITEM,'title':'Gardening','summary':'Plant herbs','tags':['gardening'],'key_ideas':[],'concepts':[]})
    assert item['topic_ids']==['inbox'] and item['id']==ITEM['id']
    summary=topic_summary([item])
    assert next(row for row in summary if row['id']=='inbox')['count']==1
    assert next(row for row in summary if row['id']=='needs-review')['count']==0
    assert len(topic_summary([]))==7


def test_review_reasons_keep_topic_and_can_be_resolved_by_reviewed_override():
    source={**ITEM,'raw_extraction':{'curation':{'needs_review':True,'review_reasons':['Clip ends early']}}}
    item=annotate_item(source)
    assert 'agent-orchestration' in item['topic_ids'] and 'needs-review' in item['topic_ids']
    catalog=load_catalog();catalog['overrides']['v1']={'topic_ids':['integrations'],'review_reasons':[]}
    item=annotate_item(source,catalog)
    assert item['topic_ids']==['integrations'] and item['review_reasons']==[]
    assert item['organization_method']=='reviewed assignment'


def test_topic_guides_deduplicate_ideas_and_preserve_source_references():
    detail=topic_detail('agent-orchestration',[ITEM,{**ITEM,'id':'second','created_at':'2026-04-01T00:00:00Z'}])
    assert [item['id'] for item in detail['items']]==['second',ITEM['id']]
    assert len(detail['ideas'])==1 and len(detail['ideas'][0]['sources'])==2
    assert detail['actions'][0]['sources'][0]['id']=='second'
    assert topic_detail('made-up',[]) is None


@pytest.mark.parametrize('mutation',[lambda c:c['topics'].append(c['topics'][0]),lambda c:c['topics'][0].update(id='bad/slug'),lambda c:c['overrides'].update(v1={'topic_ids':['missing']})])
def test_catalog_rejects_invalid_changes(tmp_path,mutation):
    catalog=load_catalog();mutation(catalog)
    path=tmp_path/'catalog.json';path.write_text(json.dumps(catalog))
    with pytest.raises(ValueError):load_catalog(path)


def test_review_snapshot_finds_repeated_unclassified_tags_without_writes():
    items=[{**ITEM,'id':str(i),'title':'Botany','summary':'Plant herbs','tags':['gardening'],'key_ideas':[],'concepts':[]} for i in range(3)]
    before=copy.deepcopy(items);result=review_snapshot(items)
    assert len(result['queues'])==3 and result['possible_new_topics']==[{'tag':'gardening','count':3}]
    assert items==before


def test_public_routes_share_topic_classification_and_unknown_topics_are_404(monkeypatch):
    db=FakeSupabase();db.tables['knowledge_items']=[ITEM]
    monkeypatch.setattr(topics_router,'get_supabase',lambda:db)
    monkeypatch.setattr(items_router,'get_supabase',lambda:db)
    client=TestClient(app)
    response=client.get('/api/topics')
    assert response.status_code==200 and response.headers['Cache-Control']=='no-store'
    assert client.get('/api/topics/agent-orchestration').json()['items'][0]['id']==ITEM['id']
    assert client.get('/api/topics/no-such-topic').status_code==404
    assert 'agent-orchestration' in client.get('/api/items').json()[0]['topic_ids']
    assert client.get('/api/items/'+ITEM['id']).json()['item']['topics'][0]['name']=='Agents & orchestration'


def import_fixture():
    db=FakeSupabase()
    video={'id':'v1','status':'completed','transcript':'Stored source','caption':None,'instagram_url':'https://www.instagram.com/reel/Example/?tracking=yes','processed_at':'2026-03-01T00:00:00Z'}
    db.tables={'videos':[video],'knowledge_items':[],'tools':[{'id':'tool','name':'Existing'}],'user_interactions':[{'id':'i','tool_id':'tool','status':'implemented','notes':'Keep'}]}
    entry={'video_id':'v1','source_sha256':source_digest(video),'knowledge':{'title':'Source review','summary':'A source-based summary','key_ideas':['An idea']},'review_reasons':['Incomplete source']}
    return db,entry


def test_import_dry_run_cannot_write_or_call_ai():
    db,entry=import_fixture();before=copy.deepcopy(db.tables)
    result=import_reviewed(db,[entry])
    assert result['planned_count']==1 and result['inserted_count']==0 and db.tables==before


def test_import_is_idempotent_and_preserves_dates_sources_and_user_interactions():
    db,entry=import_fixture();tools=copy.deepcopy(db.tables['tools']);interactions=copy.deepcopy(db.tables['user_interactions'])
    assert import_reviewed(db,[entry],apply=True)['inserted_count']==1
    row=db.tables['knowledge_items'][0]
    assert row['created_at']=='2026-03-01T00:00:00Z'
    assert row['source_url']=='https://www.instagram.com/reel/Example/'
    assert row['raw_extraction']['curation']['review_reasons']==['Incomplete source']
    assert import_reviewed(db,[entry],apply=True)['inserted_count']==0
    assert len(db.tables['knowledge_items'])==1 and db.tables['tools']==tools and db.tables['user_interactions']==interactions


@pytest.mark.parametrize('mutation',[lambda e:e.update(source_sha256='changed'),lambda e:e.update(video_id='unknown'),lambda e:e['knowledge'].update(title=''),lambda e:e.update(review_reasons='not-a-list')])
def test_invalid_reviewed_input_does_not_write(mutation):
    db,entry=import_fixture();mutation(entry)
    with pytest.raises(ValueError):import_reviewed(db,[entry],apply=True)
    assert db.tables['knowledge_items']==[]


def test_source_change_and_duplicate_input_require_review_again():
    db,entry=import_fixture();db.tables['videos'][0]['transcript']='Changed'
    with pytest.raises(ValueError,match='changed after review'):import_reviewed(db,[entry],apply=True)
    db,entry=import_fixture()
    with pytest.raises(ValueError,match='Duplicate video'):import_reviewed(db,[entry,entry],apply=True)
    assert db.tables['knowledge_items']==[]


def test_standalone_tool_documents_inherit_source_review_limitations():
    db,entry=import_fixture()
    db.tables['tools'][0]['source_video_ids']=['v1']
    import_reviewed(db,[entry],apply=True)
    source=next(row for row in load_repository(db) if row['id']=='tool:tool')
    assert source['review_reasons']==['Incomplete source']
    assert source['topics']
