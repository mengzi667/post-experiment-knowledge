import copy
import json
from pathlib import Path
import pytest
from expkm.store import Store
from expkm.templates import Templates,default_template
from expkm.destinations import Destinations,DestinationRequired,DestinationTargetRequired
from expkm.cli import parser,run,save_private,main
from expkm.selections import SelectionRequired


def template(store,topic='quality'):
    t=Templates(store);p=t.propose(topic,default_template(),'synthetic-selection');t.confirm(topic,p,p['version'])


def local(store,name='report.md'):
    return {'mode':'markdown','markdown':{'target':str(store.root/name),'root':str(store.root)},'archives':{'scope':'none'}}


def selected(store,topic='quality',definition=None):
    d=Destinations(store);p=d.propose(topic,definition or local(store));assert p
    return d.confirm(topic,p,p['version'])


def cli(store,*args):
    return run(parser().parse_args(['--store',str(store.root),*map(str,args)]))


def test_no_implicit_save_method_and_proposal_does_not_confirm_or_write(tmp_path):
    store=Store(tmp_path/'private');d=Destinations(store)
    with pytest.raises(DestinationRequired):d.require('quality')
    p=d.propose('quality',local(store));assert p
    with pytest.raises(DestinationRequired):d.require('quality')
    assert not (store.root/'report.md').exists()
    with pytest.raises(ValueError):d.confirm('quality',p,'unreviewed')


def test_destination_reuse_and_changes_are_topic_bound_and_version_checked(tmp_path):
    store=Store(tmp_path/'private');old=selected(store);d=Destinations(store)
    assert d.require('quality')==old
    with pytest.raises(DestinationRequired):d.require('other-topic')
    p=d.propose('quality',{'mode':'feishu','feishu':{'document':'synthetic-doc'},'archives':{'scope':'none'}});assert p
    assert d.require('quality')==old
    with pytest.raises(ValueError):d.confirm('quality',p,p['version'])
    new=d.confirm('quality',p,p['version'],old['version'])
    assert new!=old and d.require('quality')==new


def test_local_location_gate_precedes_experiment_read_and_mlflow(tmp_path):
    store=Store(tmp_path/'private');template(store)
    missing=tmp_path/'does-not-exist.json'
    with pytest.raises(SelectionRequired):cli(store,'record','--topic','quality','--source-id','one','--file',missing,'--root',tmp_path)
    with pytest.raises(SelectionRequired):cli(store,'capture-mlflow','--topic','quality','--run','synthetic')
    assert store.records()==[]


def test_cli_preview_confirmation_and_prepared_bundle_reuse(tmp_path):
    store=Store(tmp_path/'private');template(store)
    p=cli(store,'destination','preview','--topic','quality','--mode','markdown','--target',store.root/'report.md','--root',store.root,'--archive-scope','none')
    assert p['status']=='needs_destination_confirmation'
    assert cli(store,'synthesize','--topic','quality','--prepare')['status']=='needs_agent_synthesis'
    confirmed=cli(store,'destination','confirm','--topic','quality','--proposal',p['proposal'],'--approve',p['version'])
    assert confirmed['status']=='destination_confirmed'
    out=cli(store,'synthesize','--topic','quality','--prepare')
    bundle=json.loads(Path(out['output']).read_text(encoding='utf-8'))
    assert bundle['report_destination']['version']==p['version']
    assert cli(store,'destination','show','--topic','quality')['version']==p['version']


def test_saved_markdown_target_is_used_and_overrides_are_rejected(tmp_path):
    store=Store(tmp_path/'private');template(store);binding=selected(store)
    content=store.root/'preview.md';content.write_text('Synthetic main report')
    p=cli(store,'sync','plan','--topic','quality','--content',content)
    plan=json.loads(Path(p['output']).read_text(encoding='utf-8'))
    assert plan['report_destination']=={'topic':'quality','version':binding['version']}
    assert cli(store,'sync','apply','--plan',p['output'],'--approve',p['plan_id'])['verified']
    assert (store.root/'report.md').exists()
    with pytest.raises(ValueError):cli(store,'sync','plan','--topic','quality','--content',content,'--target',store.root/'other.md')
    with pytest.raises(ValueError):cli(store,'sync','plan','--topic','quality','--adapter','feishu','--target','unselected','--replacements',store.root/'missing.json')


def test_changed_destination_blocks_old_apply_but_preserves_rollback(tmp_path):
    store=Store(tmp_path/'private');template(store);old=selected(store)
    content=store.root/'preview.md';content.write_text('Synthetic report')
    p=cli(store,'sync','plan','--topic','quality','--content',content)
    cli(store,'sync','apply','--plan',p['output'],'--approve',p['plan_id'])
    d=Destinations(store);proposal=d.propose('quality',local(store,'new-report.md'));assert proposal
    d.confirm('quality',proposal,proposal['version'],old['version'])
    with pytest.raises(ValueError):cli(store,'sync','apply','--plan',p['output'],'--approve',p['plan_id'])
    assert cli(store,'sync','rollback','--plan',p['output'],'--approve',p['plan_id'])['restored']
    assert not (store.root/'report.md').exists()


def test_both_needs_explicit_plan_adapter_and_feishu_choice_does_not_write(tmp_path,monkeypatch):
    store=Store(tmp_path/'private');template(store)
    definition={**local(store),'mode':'both','feishu':{'document':'synthetic-doc'}}
    selected(store,definition=definition)
    with pytest.raises(DestinationTargetRequired):cli(store,'sync','plan','--topic','quality','--content',store.root/'missing.md')
    attempts=[]
    def client(document,allowed,workspace,write_enabled=False):
        attempts.append((document,write_enabled));raise ValueError('No authorized remote setup')
    import expkm.feishu as feishu
    monkeypatch.setattr(feishu,'LarkDocument',client)
    with pytest.raises(ValueError):cli(store,'sync','plan','--topic','quality','--adapter','feishu','--replacements',store.root/'missing.json')
    assert attempts==[('synthetic-doc',False)]


def test_destination_validation_protects_public_code_and_unreviewed_changes(tmp_path):
    store=Store(tmp_path/'private');d=Destinations(store)
    public=Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError):d.propose('quality',{'mode':'markdown','markdown':{'target':str(public/'README.md'),'root':str(public)},'archives':{'scope':'none'}})
    with pytest.raises(ValueError):d.propose('quality',{'mode':'both','feishu':{'document':'synthetic-doc'}})
    p=d.propose('quality',local(store));assert p
    changed=copy.deepcopy(p);changed['definition']['markdown']['target']=str(store.root/'unreviewed.md')
    with pytest.raises(ValueError):d.confirm('quality',changed,p['version'])
    binding=d.confirm('quality',p,p['version'])
    with pytest.raises(ValueError):save_private(store,store.root/'destinations'/'quality'/'head.json',{'version':'forged'})
    assert d.require('quality')==binding


def test_noninteractive_call_reports_missing_destination_without_payload(tmp_path,capsys):
    store=Store(tmp_path/'private');template(store)
    content=store.root/'preview.md';content.write_text('Synthetic report')
    code=main(['--store',str(store.root),'sync','plan','--topic','quality','--content',str(content)])
    assert code==2
    assert json.loads(capsys.readouterr().out)['status']=='needs_destination_selection'


def test_feishu_only_routes_to_selected_document_without_local_target_or_write(tmp_path,monkeypatch):
    from test_sync import FakeDocument
    store=Store(tmp_path/'private');template(store)
    binding=selected(store,definition={'mode':'feishu','feishu':{'document':'synthetic-doc'},'archives':{'scope':'none'}})
    replacements=store.root/'replacements.json';replacements.write_text(json.dumps({'a':'<p>Synthetic revised conclusion</p>'}))
    document=FakeDocument();document.document='synthetic-doc'
    calls=[]
    def client(target,allowed,workspace,write_enabled=False):
        calls.append((target,write_enabled));return document
    import expkm.feishu as feishu
    monkeypatch.setattr(feishu,'LarkDocument',client)
    result=cli(store,'sync','plan','--topic','quality','--replacements',replacements)
    p=json.loads(Path(result['output']).read_text(encoding='utf-8'))
    assert p['adapter']=='feishu' and p['target']=='synthetic-doc'
    assert p['report_destination']['version']==binding['version']
    assert calls==[('synthetic-doc',False)] and document.writes==0


def test_new_plan_cannot_reuse_an_unrelated_loaded_plan(tmp_path,monkeypatch):
    store=Store(tmp_path/'private');template(store);selected(store)
    unrelated=store.root/'unrelated.json';unrelated.write_text('{"adapter":"feishu","target":"unselected"}')
    attempts=[]
    def client(*args,**kwargs):
        attempts.append(args);raise ValueError('Unselected remote target')
    import expkm.feishu as feishu
    monkeypatch.setattr(feishu,'LarkDocument',client)
    with pytest.raises(ValueError):cli(store,'sync','plan','--topic','quality','--plan',unrelated)
    assert not attempts


def test_legacy_destination_needs_upload_scope_choice_without_erasing_old_binding(tmp_path):
    from expkm.common import digest,write_json
    from expkm.onboarding import setup_status
    store=Store(tmp_path/'private');template(store)
    legacy={'schema_version':1,'topic':'quality','definition':{'mode':'feishu','feishu':{'document':'synthetic-doc'}}}
    legacy['version']=digest(legacy);folder=store.root/'destinations'/'quality'
    write_json(folder/(legacy['version']+'.json'),legacy);write_json(folder/'head.json',{'version':legacy['version']})
    d=Destinations(store)
    assert d.require('quality')==legacy
    assert not setup_status(store,'quality','sync','report')['questions']
    assert [q['id'] for q in setup_status(store,'quality','sync','archive')['questions']]==['archive_scope','archive_location']
    p=d.propose('quality',{**legacy['definition'],'archives':{'scope':'none'}})
    d.confirm('quality',p,p['version'],legacy['version'])
    assert d.get('quality',legacy['version'])==legacy
