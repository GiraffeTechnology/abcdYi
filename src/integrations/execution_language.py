"""Canonicalize execution input before any business mutation or DB write."""
from __future__ import annotations
import hashlib
import os
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from aivan.integrations.language_skill_client import LanguageSkillClient
from src.execution_graph.writer import emit_event


def _error(code, status=503):
    raise HTTPException(status_code=status, detail={'error':code})


def _convert(payload, table):
    if os.environ.get('ABCDYI_EXECUTION_LANGUAGE_TEST_MODE') == '1' and os.environ.get('AIVAN_ENV') == 'test':
        return payload, []
    url = os.environ.get('AIVAN_LANGUAGE_SKILL_BASE_URL') or os.environ.get('GIRAFFE_LANGUAGE_SKILL_URL')
    if not url:
        _error('EXECUTION_LANGUAGE_SERVICE_REQUIRED')
    client = LanguageSkillClient(base_url=url)
    def validate(value):
        result = client._request('POST', '/api/language/canonical-db/validate', json={
            'repository':'abcdYi','table_name':'abcdyi_lifecycle.'+table,
            'record':value,'policy':'standard_english_canonical_db_v1'})
        if not result.ok or not isinstance(result.data,dict) or type(result.data.get('valid')) is not bool:
            _error('EXECUTION_LANGUAGE_VALIDATION_UNAVAILABLE')
        return result.data
    verdict = validate(payload)
    if verdict['valid']:
        if verdict.get('violations'):
            _error('EXECUTION_LANGUAGE_RESPONSE_INVALID')
        return payload, []
    fields = {item.get('field') for item in verdict.get('violations',[]) if isinstance(item,dict)}
    if not fields:
        _error('EXECUTION_LANGUAGE_RESPONSE_INVALID')
    evidence=[]
    def walk(value,key,path):
        if isinstance(value,dict):return {k:walk(v,k,path+'.'+k) for k,v in value.items()}
        if isinstance(value,list):return [walk(v,key,path+f'[{i}]') for i,v in enumerate(value)]
        if not isinstance(value,str) or path not in fields:return value
        # Identity, protocol and reference values must not be rewritten as prose.
        if key.endswith(('_id','_ids','_hash','_sha256','_at','_date')) or key in {'status','event_type','action','tracking_number','image_path','url','storage_reference'}:
            _error('EXECUTION_LANGUAGE_INVALID_TECHNICAL_VALUE',422)
        result=client.normalize(value,source_language='auto',canonical_language='en',domain_hint='apparel_execution')
        canonical=result.data.get('canonical_text') if result.ok and isinstance(result.data,dict) else None
        if not isinstance(canonical,str) or not canonical.strip():
            _error('EXECUTION_LANGUAGE_NORMALIZATION_REQUIRED')
        evidence.append({'field_path':path,'source_sha256':hashlib.sha256(value.encode()).hexdigest(),
                         'canonical_sha256':hashlib.sha256(canonical.encode()).hexdigest()})
        return canonical
    normalized=walk(payload,'','abcdyi_lifecycle.'+table)
    checked=validate(normalized)
    if checked['valid'] is not True or checked.get('violations'):
        _error('EXECUTION_CANONICAL_ENGLISH_REQUIRED',422)
    return normalized,evidence


async def normalize_execution_input(body, table):
    payload,evidence=await run_in_threadpool(_convert,body.model_dump(mode='json'),table)
    return type(body).model_validate(payload),evidence


async def record_input_lineage(db, evidence, *, tenant_id, user_id, order_id):
    if evidence:
        await emit_event(db,'EXECUTION_INPUT_NORMALIZED',{'fields':evidence},tenant_id=tenant_id,
                         order_id=order_id,triggered_by_user_id=user_id)
