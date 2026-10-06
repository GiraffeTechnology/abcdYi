"""Language normalization precedes workflow and stores hashes, never originals."""
import hashlib
import json
import uuid
from sqlalchemy import select
from src.db.models import Milestone, ExecutionEvent
from tests.api.test_provider_order_handoff import handoff, import_order
from aivan.integrations.language_skill_client import LanguageSkillResult


async def test_non_english_execution_input_is_normalized_before_storage(handoff,monkeypatch):
    client,provider,sessions,_,_=handoff
    order=(await import_order(client)).json()
    async with sessions() as db:
        ms=await db.scalar(select(Milestone).where(Milestone.order_id==uuid.UUID(order['id'])))
        mid=str(ms.id)
    monkeypatch.delenv('ABCDYI_EXECUTION_LANGUAGE_TEST_MODE')
    monkeypatch.setenv('AIVAN_LANGUAGE_SKILL_BASE_URL','http://synthetic-language.invalid')
    original='\u5305\u88c5\u5df2\u5b8c\u6210'
    from aivan.integrations.language_skill_client import LanguageSkillClient
    def validate(self,method,path,json=None):
        record=json['record'];non_english=original in str(record)
        return LanguageSkillResult(True,{'valid':not non_english,'violations':[{'field':'abcdyi_lifecycle.milestones.notes','reason':'non_english'}] if non_english else []},None,200)
    def normalize(self,text,**kwargs):
        assert text==original
        return LanguageSkillResult(True,{'canonical_text':'Packing has been completed.'},None,200)
    monkeypatch.setattr(LanguageSkillClient,'_request',validate);monkeypatch.setattr(LanguageSkillClient,'normalize',normalize)
    response=await client.patch(f'/api/milestones/{mid}',json={'notes':original})
    assert response.status_code==200,response.text
    async with sessions() as db:
        ms=await db.get(Milestone,uuid.UUID(mid));assert ms.notes=='Packing has been completed.'
        event=await db.scalar(select(ExecutionEvent).where(ExecutionEvent.event_type=='EXECUTION_INPUT_NORMALIZED'))
        assert event.payload['fields'][0]['source_sha256']==hashlib.sha256(original.encode()).hexdigest()
        assert original not in json.dumps(event.payload,ensure_ascii=False)
    assert original not in json.dumps(provider.state,ensure_ascii=False)


async def test_missing_translation_weights_never_persist_original(handoff,monkeypatch):
    client,_,sessions,_,_=handoff
    order=(await import_order(client)).json()
    async with sessions() as db:
        ms=await db.scalar(select(Milestone).where(Milestone.order_id==uuid.UUID(order['id'])));mid=str(ms.id);before=ms.notes
    monkeypatch.delenv('ABCDYI_EXECUTION_LANGUAGE_TEST_MODE')
    monkeypatch.setenv('AIVAN_LANGUAGE_SKILL_BASE_URL','http://synthetic-language.invalid')
    from aivan.integrations.language_skill_client import LanguageSkillClient
    monkeypatch.setattr(LanguageSkillClient,'_request',lambda *a,**k:LanguageSkillResult(True,{'valid':False,'violations':[{'field':'abcdyi_lifecycle.milestones.notes','reason':'non_english'}]},None,200))
    monkeypatch.setattr(LanguageSkillClient,'normalize',lambda *a,**k:LanguageSkillResult(False,None,'model unavailable',503))
    r=await client.patch(f'/api/milestones/{mid}',json={'notes':'\u5305\u88c5\u5df2\u5b8c\u6210'})
    assert r.status_code==503,r.text
    async with sessions() as db:assert (await db.get(Milestone,uuid.UUID(mid))).notes==before


def test_isolated_test_flag_cannot_bypass_production(monkeypatch):
    from src.integrations.execution_language import _convert
    from fastapi import HTTPException
    import pytest
    monkeypatch.setenv('AIVAN_ENV','production');monkeypatch.setenv('ABCDYI_EXECUTION_LANGUAGE_TEST_MODE','1')
    monkeypatch.delenv('AIVAN_LANGUAGE_SKILL_BASE_URL',raising=False);monkeypatch.delenv('GIRAFFE_LANGUAGE_SKILL_URL',raising=False)
    with pytest.raises(HTTPException) as exc:_convert({'notes':'Packing completed.'},'milestones')
    assert exc.value.status_code==503
