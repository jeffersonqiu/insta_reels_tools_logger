from fastapi import APIRouter, HTTPException, Response
from fastapi.encoders import jsonable_encoder

from db.client import get_supabase
from services.knowledge_repository import _rows, ITEM_FIELDS
from services.organization import topic_detail, topic_summary

router = APIRouter(prefix='/topics', tags=['topics'])


def _items():
    return _rows(get_supabase(), 'knowledge_items', ITEM_FIELDS)


@router.get('')
def list_topics(response: Response):
    response.headers['Cache-Control'] = 'no-store'
    return jsonable_encoder(topic_summary(_items()))


@router.get('/{topic_id}')
def get_topic(topic_id: str, response: Response):
    response.headers['Cache-Control'] = 'no-store'
    result = topic_detail(topic_id, _items())
    if result is None:
        raise HTTPException(status_code=404, detail='Topic not found')
    return jsonable_encoder(result)
