import copy
import json
from pathlib import Path
import pytest
from expkm.store import Store
from expkm.templates import Templates,TemplateRequired,default_template
from expkm.knowledge import Knowledge,render
from expkm.cli import parser,run
from expkm.destinations import Destinations
from test_knowledge import metadata,draft

def approve(store, topic='quality', definition=None):
    templates=Templates(store)
    p=templates.propose(topic,definition or default_template(),'synthetic-user-selected-template')
    assert p
    return templates.confirm(topic,p,p['version'])

def recorded(tmp_path):
    root=tmp_path/'input';root.mkdir();file=root/'r.json';file.write_text('{"score":0.8}')
    store=Store(tmp_path/'private')
    return store,store.record('quality','one',metadata(),[file],[root])

def save_locally(root):
    store=Store(root);d=Destinations(store)
    p=d.propose('quality',{'mode':'markdown','markdown':{'target':str(store.root/'report.md'),'root':str(store.root)},'archives':{'scope':'none'}})
    d.confirm('quality',p,p['version'])

def test_first_use_requires_selection_without_implicitly_using_builtin(tmp_path):
    store=Store(tmp_path/'private');t=Templates(store)
    with pytest.raises(TemplateRequired):t.require('quality')
    p=t.propose('quality',default_template(),'user-provided')
    assert p
    with pytest.raises(TemplateRequired):t.require('quality')
    with pytest.raises(ValueError):t.confirm('quality',p,'not-approved')
    with pytest.raises(TemplateRequired):t.require('quality')

def test_confirmed_topic_reuses_exact_frozen_template(tmp_path):
    store=Store(tmp_path/'private');binding=approve(store);assert binding
    first=Templates(store).require('quality');second=Templates(store).require('quality')
    assert first==second and first['version']==binding['version']

def test_source_change_and_switch_need_new_confirmation_and_cas(tmp_path):
    store=Store(tmp_path/'private');first=approve(store);assert first
    altered=default_template();altered['name']='Revised template'
    t=Templates(store);p=t.propose('quality',altered,'new-source-version');assert p
    assert t.require('quality')['version']==first['version']
    with pytest.raises(ValueError):t.confirm('quality',p,p['version'])
    current=t.confirm('quality',p,p['version'],first['version'])
    assert current['version']!=first['version']

def test_cli_refuses_record_before_reading_experiment_when_local_location_unset(tmp_path):
    store=tmp_path/'private';root=tmp_path/'input';root.mkdir();file=root/'bad.json';file.write_text('not json')
    args=parser().parse_args(['--store',str(store),'record','--topic','quality','--source-id','one','--file',str(file),'--root',str(root)])
    from expkm.selections import SelectionRequired
    with pytest.raises(SelectionRequired):run(args)
    assert Store(store).records()==[]

def test_knowledge_without_report_is_template_independent(tmp_path):
    store,row=recorded(tmp_path)
    state=Knowledge(store).update('quality',draft([row]))
    assert state['report_template'] is None
    with pytest.raises(TemplateRequired):render(state)

def test_render_obeys_builtin_structure_and_preserves_flexible_result_blocks(tmp_path):
    store,row=recorded(tmp_path);binding=approve(store);assert binding
    d=draft([row]);d['report_sections']={
        'environment':[{'type':'table','columns':['配置项','实际值'],'rows':[['rank','8']]}],
        'main_results':[{'type':'table','columns':['实验自定义指标','结果'],'rows':[['custom-score','0.8']]}, {'type':'paragraph','text':'结果形式由本次实验决定。'}],
        'limitations':[{'type':'paragraph','text':'仅适用于冻结验证集。'}]}
    state=Knowledge(store).update('quality',d)
    text=render(state)
    headings=['## 1. 测试概述','## 2. 测试设计','## 3. 测试结果','## 4. 分析与限制','## 5. 决策与后续','## 附录：复现与证据']
    positions=[text.index(h) for h in headings]
    assert positions==sorted(positions)
    assert '| rank | 8 |' in text and '| custom-score | 0.8 |' in text
    assert '仅适用于冻结验证集。' in text
    assert state['report_template']['version']==binding['version']

def test_render_has_no_unconfirmed_legacy_fallback():
    with pytest.raises(TemplateRequired):render({'topic':'quality','claims':[],'decisions':[]})

def test_custom_template_heading_order_is_respected_and_snapshot_is_pinned(tmp_path):
    store,row=recorded(tmp_path);custom=default_template()
    custom['sections'][1]['title']='A. Experiment context'
    binding=approve(store,definition=custom);assert binding
    state=Knowledge(store).update('quality',draft([row]));text=render(state)
    assert '## A. Experiment context' in text
    assert '## 1. 测试概述' not in text
    original=copy.deepcopy(state)
    custom['name']='Another version';p=Templates(store).propose('quality',custom,'next');assert p
    Templates(store).confirm('quality',p,p['version'],binding['version'])
    assert render(original)==text

def test_unknown_section_and_template_mutation_are_rejected(tmp_path):
    store,row=recorded(tmp_path);binding=approve(store);assert binding
    d=draft([row]);d['report_sections']={'invented':[{'type':'paragraph','text':'lost content'}]}
    with pytest.raises(ValueError):Knowledge(store).update('quality',d)
    p=Templates(store).propose('quality',default_template(),'source');assert p
    p['definition']['name']='Changed after review'
    with pytest.raises(ValueError):Templates(store).confirm('quality',p,p['version'],binding['version'])

def test_cli_template_selection_is_explicit_and_prepare_contains_frozen_binding(tmp_path):
    store=tmp_path/'private'
    def cli(*argv):return run(parser().parse_args(['--store',str(store),*map(str,argv)]))
    proposal=cli('template','preview','--topic','quality','--builtin')
    assert cli('synthesize','--topic','quality','--prepare')['status']=='needs_agent_synthesis'
    cli('template','confirm','--topic','quality','--proposal',proposal['proposal'],'--approve',proposal['version'])
    save_locally(store)
    output=cli('synthesize','--topic','quality','--prepare')
    assert json.loads(Path(output['output']).read_text(encoding='utf-8'))['report_template']['version']==proposal['version']

def test_sync_requires_template_and_stale_plan_cannot_write_but_can_rollback(tmp_path):
    store=Store(tmp_path/'private');target=store.root/'report.md';content=store.root/'preview.md';content.write_text('Synthetic content')
    def cli(*argv):return run(parser().parse_args(['--store',str(store.root),*map(str,argv)]))
    argv=['sync','plan','--topic','quality','--target',target,'--content',content,'--root',store.root]
    with pytest.raises(TemplateRequired):cli(*argv)
    assert not target.exists()
    first=approve(store);save_locally(store.root);p=cli(*argv)
    assert cli('sync','apply','--plan',p['output'],'--approve',p['plan_id'])['verified']
    changed=default_template();changed['name']='Next'
    proposal=Templates(store).propose('quality',changed,'next')
    Templates(store).confirm('quality',proposal,proposal['version'],first['version'])
    with pytest.raises(ValueError):cli('sync','apply','--plan',p['output'],'--approve',p['plan_id'])
    assert cli('sync','rollback','--plan',p['output'],'--approve',p['plan_id'])['restored']
    assert not target.exists()

def test_cli_local_location_gate_happens_before_mlflow_configuration_or_network(tmp_path):
    args=parser().parse_args(['--store',str(tmp_path/'private'),'capture-mlflow','--topic','q','--run','synthetic'])
    from expkm.selections import SelectionRequired
    with pytest.raises(SelectionRequired):run(args)

def test_mutable_exports_cannot_replace_template_confirmation(tmp_path):
    from expkm.cli import save_private
    store=Store(tmp_path/'private');binding=approve(store)
    with pytest.raises(ValueError):save_private(store,store.root/'templates'/'quality'/'head.json',{'version':'forged'})
    assert Templates(store).require('quality')==binding

def test_filled_report_content_cannot_disappear_without_revision_reason(tmp_path):
    store,row=recorded(tmp_path);approve(store);d=draft([row])
    d['report_sections']={'limitations':[{'type':'paragraph','text':'Important known boundary.'}]}
    old=Knowledge(store).update('quality',d)
    new=Knowledge(store).update('quality',draft([row]),old['version'])
    assert new['report_sections']==old['report_sections']
    cleared=draft([row]);cleared['report_sections']={}
    with pytest.raises(ValueError):Knowledge(store).update('quality',cleared,new['version'])
