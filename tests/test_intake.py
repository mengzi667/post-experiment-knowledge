"""Synthetic request intake contracts: no real sources or platform accounts."""
import copy
import json
import os
from pathlib import Path
import pytest
from expkm.store import Store
from expkm.templates import Templates, default_template, TemplateRequired
from expkm.selections import Selections, SelectionRequired
from expkm.cli import parser, run


def request(store, **overrides):
    return {'request_id':'synthetic-request-one','topic':'quality',
            'goal':'Preserve and analyze existing synthetic results',
            'scope':'Explicit synthetic input root and all existing topic evidence',
            'requirements':['Preserve originals','No experiment execution'],
            'stages':['record','synthesize','sync'],
            'source_roots':[str(store.root.parent)],
            'all_topic_records':True,'reports':[],'archives':'none',**overrides}


def preferences(store):
    t=Templates(store);p=t.propose('quality',default_template(),'synthetic-user-provided-template')
    t.confirm('quality',p,p['version'])
    s=Selections(store,'record-location');p=s.propose('quality',{'store':str(store.root).removeprefix('\\\\?\\')})
    s.confirm('quality',p,p['version'])


def confirm(store, definition=None):
    from expkm.intake import Intakes
    intake=Intakes(store);p=intake.propose(definition or request(store))
    return intake.confirm(p,p['version'])


def test_missing_template_or_exact_store_blocks_even_record_and_analysis(tmp_path):
    from expkm.intake import Intakes
    store=Store(tmp_path/'private')
    with pytest.raises(TemplateRequired):Intakes(store).propose(request(store))
    t=Templates(store);p=t.propose('quality',default_template(),'synthetic-template');t.confirm('quality',p,p['version'])
    with pytest.raises(SelectionRequired):Intakes(store).propose(request(store))


def test_preferences_do_not_authorize_a_new_request_or_read_input(tmp_path):
    from expkm.intake import IntakeRequired
    store=Store(tmp_path/'private');preferences(store)
    for args in [
        ['record','--topic','quality','--source-id','one','--file',str(tmp_path/'missing.json'),'--root',str(tmp_path)],
        ['synthesize','--topic','quality','--prepare'],
        ['organize','--topic','quality','--input',str(tmp_path/'missing.xml'),'--out',str(store.root/'out.json')],
        ['capture-mlflow','--topic','quality','--run','synthetic'],
    ]:
        with pytest.raises(IntakeRequired):
            run(parser().parse_args(['--store',str(store.root),*args]))


def test_scope_requirements_are_mandatory_and_proposal_is_not_confirmation(tmp_path):
    from expkm.intake import Intakes, IntakeRequired
    store=Store(tmp_path/'private');preferences(store);i=Intakes(store)
    for name,invalid in [('goal',''),('scope',''),('requirements',[]),('stages',[]),('request_id','')]:
        with pytest.raises(ValueError):i.propose(request(store,**{name:invalid}))
    p=i.propose(request(store))
    with pytest.raises(IntakeRequired):i.require(p['version'],'record','quality')
    changed=copy.deepcopy(p);changed['definition']['scope']='Unreviewed extra scope'
    with pytest.raises(ValueError):i.confirm(changed,p['version'])


def test_explicit_request_confirmation_is_bound_to_stage_and_current_versions(tmp_path):
    from expkm.intake import Intakes
    store=Store(tmp_path/'private');preferences(store)
    approved=confirm(store,request(store,stages=['record']))
    intake=Intakes(store)
    assert intake.require(approved['version'],'record','quality')
    with pytest.raises(ValueError):intake.require(approved['version'],'synthesize','quality')
    with pytest.raises(ValueError):intake.require(approved['version'],'record','another-topic')
    t=Templates(store);old=t.require('quality');definition=default_template();definition['name']='Changed template'
    p=t.propose('quality',definition,'synthetic-new-template');t.confirm('quality',p,p['version'],old['version'])
    with pytest.raises(ValueError):intake.require(approved['version'],'record','quality')


def test_closed_intake_cannot_be_reused_as_a_new_task(tmp_path):
    from expkm.intake import Intakes
    store=Store(tmp_path/'private');preferences(store);approved=confirm(store)
    i=Intakes(store);i.close(approved['version'])
    with pytest.raises(ValueError):i.require(approved['version'],'record','quality')
    with pytest.raises(ValueError):i.confirm(approved,approved['version'])


def test_confirmed_intake_allows_record_but_refuses_out_of_scope_roots(tmp_path):
    store=Store(tmp_path/'private');preferences(store);allowed=tmp_path/'authorized';allowed.mkdir()
    approved=confirm(store,request(store,source_roots=[str(allowed)],stages=['record']))
    file=allowed/'result.json';file.write_text('{"status":"completed","score":0.8}')
    def call(file,root):
        return run(parser().parse_args(['--store',str(store.root),'--intake',approved['version'],'record',
                    '--topic','quality','--source-id','one','--file',str(file),'--root',str(root)]))
    row=call(file,allowed);assert store.verify(row['record_id'])['verified']
    outside=tmp_path/'outside.json';outside.write_text('{}')
    with pytest.raises(ValueError):call(outside,tmp_path)


def test_each_entry_returns_mandatory_request_template_and_location_questions(tmp_path):
    from expkm.onboarding import setup_status
    store=Store(tmp_path/'private')
    for stage in ['workflow','record','synthesize','sync']:
        value=setup_status(store,'quality',stage)
        ids={q['id'] for q in value['questions']}
        assert {'requirements','template','record_location'}<=ids
        assert value['execution_allowed'] is False


def test_archive_plan_retains_reviewed_size_budget(tmp_path):
    from expkm.archives import ArchiveSync
    from test_archives import project, Drive
    store,_=project(tmp_path)
    p=ArchiveSync(store,Drive()).plan('quality',max_bytes=12345678)
    assert p['max_bytes']==12345678


def test_workflow_rebuild_inherits_archive_plan_budget(tmp_path,monkeypatch):
    from expkm.archives import ArchiveSync
    from expkm.workflow import check
    from expkm.common import write_json
    from test_archives import project,Drive
    import expkm.drive as adapter
    store,_=project(tmp_path);drive=Drive();sync=ArchiveSync(store,drive)
    plan=sync.plan('quality',max_bytes=12345678)
    sync.apply(plan,plan['plan_id'])
    file=store.root/'archive-plan.json';write_json(file,plan)
    monkeypatch.setattr(adapter,'LarkDrive',lambda *a,**k:drive)
    original=ArchiveSync.plan;budgets=[]
    def observing(self,topic,max_bytes=100_000_000):
        budgets.append(max_bytes)
        return original(self,topic,max_bytes)
    monkeypatch.setattr(ArchiveSync,'plan',observing)
    value=check(store,{'topic':'quality','stages':['sync'],'reports':[],'archives':'full','archive_plan':str(file)})
    assert value['verified'] and budgets==[12345678]


def test_recommended_template_needs_narrow_readonly_phase_then_final_confirmation(tmp_path):
    from expkm.intake import Intakes
    store=Store(tmp_path/'private')
    local=Selections(store,'record-location')
    p=local.propose('quality',{'store':str(store.root).removeprefix('\\\\?\\')});local.confirm('quality',p,p['version'])
    source=tmp_path/'input';source.mkdir();file=source/'result.json';file.write_text('{"status":"completed","score":0.8}')
    definition=request(store,phase='template-recommendation',source_roots=[str(source)])
    i=Intakes(store);p=i.propose(definition);approved=i.confirm(p,p['version'])
    args=['--store',str(store.root),'--intake',approved['version']]
    with pytest.raises(ValueError):
        run(parser().parse_args([*args,'record','--topic','quality','--source-id','one','--file',str(file),'--root',str(source)]))
    value=run(parser().parse_args([*args,'template-context','--topic','quality','--file',str(file)]))
    bundle=json.loads(Path(value['output']).read_text(encoding='utf-8'))
    assert bundle['purpose']=='template_recommendation_only' and bundle['files'][0]['text']==file.read_text()
    assert store.records()==[]
    with pytest.raises(TemplateRequired):i.propose(request(store,request_id='final-execution',source_roots=[str(source)]))
    # A selected recommendation still needs the ordinary final request gate.
    t=Templates(store);p=t.propose('quality',default_template(),'synthetic-Codex-recommendation-reviewed')
    t.confirm('quality',p,p['version'])
    final=i.propose(request(store,request_id='final-execution',source_roots=[str(source)]))
    assert final['bindings']['template_version']==p['version']
    with pytest.raises(ValueError):i.require(approved['version'],'record','quality')


def test_template_cards_offer_existing_previous_and_codex_recommendation(tmp_path):
    from expkm.onboarding import setup_status
    question=next(q for q in setup_status(Store(tmp_path/'private'),'quality','record')['questions'] if q['id']=='template')
    assert len(question['options'])==3 and any('Codex' in v for v in question['options'])


def test_recommendation_phase_never_reports_formal_execution_allowed(tmp_path):
    from expkm.onboarding import setup_status
    store=Store(tmp_path/'private');preferences(store)
    approved=confirm(store,request(store,phase='template-recommendation'))
    value=setup_status(store,'quality','workflow',intake_version=approved['version'])
    assert value['recommendation_read_allowed'] is True
    assert value['execution_allowed'] is False


def test_closed_request_returns_actionable_confirmation_status(tmp_path,capsys):
    from expkm.intake import Intakes
    from expkm.cli import main
    store=Store(tmp_path/'private');preferences(store);approved=confirm(store)
    Intakes(store).close(approved['version'])
    code=main(['--store',str(store.root),'--intake',approved['version'],'synthesize','--topic','quality','--prepare'])
    result=json.loads(capsys.readouterr().out)
    assert code==2 and result['status']=='needs_request_confirmation' and result['reason']=='request_closed'


def test_current_intake_audit_cannot_omit_requested_steps_or_outputs(tmp_path):
    from expkm.common import write_json
    store=Store(tmp_path/'private');preferences(store);approved=confirm(store)
    path=store.root/'workflow.json'
    write_json(path,{'topic':'quality','stages':['record'],'source_ids':['one'],'reports':[],'archives':'none'})
    with pytest.raises(ValueError):
        run(parser().parse_args(['--store',str(store.root),'--intake',approved['version'],'workflow','--request',str(path)]))


def test_all_topic_intake_cannot_audit_only_a_partial_source_list(tmp_path):
    from expkm.common import write_json
    store=Store(tmp_path/'private');preferences(store)
    file=tmp_path/'result.txt';file.write_text('SYNTHETIC_RESULT')
    store.record('quality','one',{'status':'completed'},[file],[tmp_path])
    store.record('quality','two',{'status':'completed'},[file],[tmp_path])
    approved=confirm(store,request(store,stages=['record']))
    path=store.root/'workflow.json'
    write_json(path,{'topic':'quality','stages':['record'],'source_ids':['one'],'reports':[],'archives':'none'})
    with pytest.raises(ValueError):
        run(parser().parse_args(['--store',str(store.root),'--intake',approved['version'],'workflow','--request',str(path)]))


@pytest.mark.skipif(os.environ.get('EXPKM_TEST_LARGE_ARCHIVE')!='1',reason='Opt-in real byte-scale archive acceptance')
def test_large_archive_over_default_limit_completes_cli_audit(tmp_path,monkeypatch):
    from expkm.common import write_json
    from test_archives import Drive
    import expkm.drive as adapter
    store=Store(tmp_path/'private');preferences(store)
    selection=Selections(store,'archive-destination')
    p=selection.propose('quality',{'archives':{'scope':'full','folder':'synthetic-parent'}})
    selection.confirm('quality',p,p['version'])
    file=tmp_path/'large-result.txt'
    chunk=b'SYNTHETIC_RESULT_LINE\n'*50000
    with file.open('wb') as stream:
        for _ in range(101):stream.write(chunk)
    assert file.stat().st_size>100_000_000
    intake=confirm(store,request(store,stages=['record','sync'],archives='full',max_archive_bytes=500_000_000))
    def call(*args):
        return run(parser().parse_args(['--store',str(store.root),'--intake',intake['version'],*map(str,args)]))
    row=call('record','--topic','quality','--source-id','large-attempt','--file',file,'--root',tmp_path)
    assert store.verify(row['record_id'])['verified']
    p=call('archive','plan','--topic','quality')
    plan=json.loads(Path(p['output']).read_text(encoding='utf-8'))
    assert plan['max_bytes']==500_000_000
    drive=Drive();monkeypatch.setattr(adapter,'LarkDrive',lambda *a,**k:drive)
    assert call('archive','apply','--plan',p['output'],'--approve',p['plan_id'],'--allow-feishu-upload')['verified']
    path=store.root/'workflow.json'
    write_json(path,{'topic':'quality','stages':['record','sync'],'source_ids':['large-attempt'],
                     'reports':[],'archives':'full','archive_plan':p['output']})
    assert call('workflow','--request',path)['verified']
    assert drive.writes==1
