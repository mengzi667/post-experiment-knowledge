import copy
import pytest
from expkm.store import Store
from expkm.knowledge import Knowledge,compare,render
from expkm.templates import Templates,default_template

def metadata(value=0.8,hardware='gpu-a'):
    return {'status':'completed','comparison':{'dataset':'data-sha','split':'validation','protocol':'paired-v1','layer':'offline','aggregation':'per-round-median'},'environment':{'hardware':hardware},'config':{'rank':8},'metrics':{'score':{'value':value,'unit':'ratio','direction':'max','definition':'correct/n','denominator':30}}}

def test_comparison_retains_scope_and_does_not_make_a_decision():
    r=compare({'metadata':metadata(.8)},{'metadata':metadata(.9)},'score')
    assert r and r['comparability']=='direct' and r['metric_effect']=='improved'
    assert r['decision_changed'] is False

def test_cross_environment_comparison_is_conditional():
    r=compare({'metadata':metadata()},{'metadata':metadata(.9,'gpu-b')},'score')
    assert r and r['comparability']=='conditional'

def test_protocol_mismatch_cannot_win_a_ranking():
    other=metadata(.99);other['comparison']['protocol']='different'
    r=compare({'metadata':metadata()},{'metadata':other},'score')
    assert r and r['comparability']=='incompatible' and r['metric_effect']=='not_assessed'

def test_missing_and_zero_are_not_conflated():
    a=metadata(0);b=metadata();del b['metrics']['score']['value']
    r=compare({'metadata':a},{'metadata':b},'score')
    assert r and r['comparability']=='insufficient'

def make_records(tmp_path,count):
    source=tmp_path/'input';source.mkdir();file=source/'result.json';file.write_text('{"score":0.8}')
    store=Store(tmp_path/'private')
    templates=Templates(store);p=templates.propose('quality',default_template(),'synthetic-confirmation')
    templates.confirm('quality',p,p['version'])
    rows=[store.record('quality',f'actual-attempt-{i}',metadata(),[file],[source]) for i in range(count)]
    return store,rows

def draft(rows,text='Current evidence supports the baseline.',status='candidate'):
    return {'claims':[{'id':'claim-one','question':'quality','text':text,'status':status,'evidence':[{'record_id':r['record_id'],'revision':r['revision'],'sha256':r['evidence'][0]['sha256']} for r in rows]}],'decisions':[]}

def test_30_true_experiments_do_not_create_30_main_sections(tmp_path):
    store,rows=make_records(tmp_path,30);k=Knowledge(store)
    first=k.update('quality',draft(rows[:1]));assert first
    second=k.update('quality',draft(rows),first['version']);assert second
    doc=render(second)
    assert len(store.records())==30 and doc.count('#### quality')==1
    assert len(doc)<len(render(first))+100
    assert len(k.trace('quality','claim-one')['evidence'])==30

def test_fabricated_evidence_and_metric_values_are_rejected(tmp_path):
    store,rows=make_records(tmp_path,1);k=Knowledge(store);d=draft(rows)
    d['claims'][0]['evidence'][0]['sha256']='invented'
    with pytest.raises(ValueError):k.update('quality',d)
    d=draft(rows);d['claims'][0]['assertions']=[{'record_id':rows[0]['record_id'],'revision':rows[0]['revision'],'path':['metadata','metrics','score','value'],'value':.99}]
    with pytest.raises(ValueError):k.update('quality',d)

def test_conflicting_claim_revision_requires_reason_and_keeps_old(tmp_path):
    store,rows=make_records(tmp_path,1);k=Knowledge(store)
    old=k.update('quality',draft(rows));assert old
    d=draft(rows,'Evidence is disputed.','disputed')
    with pytest.raises(ValueError):k.update('quality',d,old['version'])
    d['reason']='New analysis identifies incompatible protocol.'
    new=k.update('quality',d,old['version'])
    assert new and len(k.history('quality'))==2
    assert k.history('quality')[0]['claims'][0]['text']!=new['claims'][0]['text']

def test_stale_knowledge_update_is_rejected(tmp_path):
    store,rows=make_records(tmp_path,1);k=Knowledge(store)
    old=k.update('quality',draft(rows));assert old
    with pytest.raises(ValueError):k.update('quality',draft(rows),None)
