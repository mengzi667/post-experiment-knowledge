import argparse
import copy
import os
from pathlib import Path
import pytest
from expkm.common import digest
from expkm.store import Store
from expkm.knowledge import Knowledge, compare
from expkm.cli import parser, run, save_private
from expkm.sync import MarkdownSync,FeishuSync,SyncConflict,sealed,b64
from test_knowledge import metadata,make_records,draft
from test_sync import FakeDocument
from expkm.templates import Templates,default_template
from expkm.destinations import Destinations
from confirmed_cli import run_confirmed

def select_template(root):
    t=Templates(Store(root));p=t.propose('q',default_template(),'synthetic-confirmation');t.confirm('q',p,p['version'])
    d=Destinations(Store(root));p=d.propose('q',{'mode':'markdown','markdown':{'target':str(root/'report.md'),'root':str(root)},'archives':{'scope':'none'}});d.confirm('q',p,p['version'])

def test_reserved_knowledge_fields_cannot_corrupt_head_or_override_topic(tmp_path):
    store,rows=make_records(tmp_path,1);k=Knowledge(store);old=k.update('quality',draft(rows))
    polluted=copy.deepcopy(old);polluted['topic']='forged'
    with pytest.raises(ValueError):k.update('quality',polluted,old['version'])
    assert k.head('quality')==old

def test_unknown_prestate_does_not_reissue_the_write(tmp_path):
    class Unknown(FakeDocument):
        def replace(self,*args):self.writes+=1;raise TimeoutError('request outcome unknown')
    c=Unknown();s=FeishuSync(c,tmp_path/'private');p=s.plan({'a':'<p>Changed</p>'})
    with pytest.raises(TimeoutError):s.apply(p,p['plan_id'])
    with pytest.raises(TimeoutError):s.apply(p,p['plan_id'])
    assert c.writes==1

def test_result_change_between_parse_and_archive_is_rejected(tmp_path,monkeypatch):
    select_template(tmp_path/'private')
    import expkm.cli as cli
    root=tmp_path/'input';root.mkdir();file=root/'result.json';file.write_text('{"score":0.8}')
    original=cli.read_result
    def change(path):
        result=original(path);file.write_text('{"score":0.2}');return result
    monkeypatch.setattr(cli,'read_result',change)
    args=parser().parse_args(['--store',str(tmp_path/'private'),'record','--topic','q','--source-id','one','--file',str(file),'--root',str(root)])
    with pytest.raises(ValueError):run(args)
    assert Store(tmp_path/'private').records()==[]

def test_blank_or_zero_comparison_identity_is_insufficient():
    a,b=metadata(.8),metadata(.9)
    for x in [a,b]:
        x['comparison']={k:'' for k in x['comparison']}
        x['metrics']['score'].update(unit='',definition='',denominator=0)
    r=compare({'metadata':a},{'metadata':b},'score')
    assert r['comparability']=='insufficient' and r['metric_effect']=='not_assessed'

def test_normal_output_cannot_overwrite_archival_evidence(tmp_path):
    store,rows=make_records(tmp_path,1);path=store.root/rows[0]['evidence'][0]['object']
    with pytest.raises(ValueError):save_private(store,path,{'not':'evidence'})
    assert store.verify(rows[0]['record_id'])['verified']
    with pytest.raises(ValueError):MarkdownSync(store.root/'sync').plan(store.root/'records'/'a.md','New',[store.root])

def test_loaded_markdown_plan_revalidates_code_root_exclusion(tmp_path):
    public=Path(__file__).parents[1];target=public/'README.md';before=target.read_bytes()
    p=sealed({'schema_version':1,'adapter':'markdown','target':str(target),'allowed_roots':[str(public)],'existed':True,'before':b64(before),'after':b64(b'bad')})
    s=MarkdownSync(tmp_path/'private')
    # Intercept at the boundary so a regression cannot actually mutate public source.
    import expkm.sync as sync
    attempted=[];original=sync.atomic_bytes
    def protect(path,raw):
        if Path(path)==target:attempted.append(path);return
        original(path,raw)
    from unittest.mock import patch
    with patch.object(sync,'atomic_bytes',protect):
        with pytest.raises(ValueError):s.apply(p,p['plan_id'])
    assert not attempted and target.read_bytes()==before

def test_feishu_initial_revision_and_block_identity_must_match(tmp_path):
    c=FakeDocument();s=FeishuSync(c,tmp_path/'private');p=s.plan({'a':'<p>Changed</p>'})
    c.revision=99;c.blocks[0]='<p id="recreated">Old conclusion</p>'
    with pytest.raises(SyncConflict):s.apply(p,p['plan_id'])
    assert c.writes==0

def test_normalized_metadata_sidecar_is_also_archived(tmp_path):
    select_template(tmp_path/'private')
    root=tmp_path/'input';root.mkdir();result=root/'result.txt';result.write_text('raw result')
    sidecar=root/'metadata.json';sidecar.write_text('{"status":"completed","config":{"rank":8}}')
    out=run_confirmed(Store(tmp_path/'private'),'record','--topic','q','--source-id','one','--file',result,'--root',root,'--metadata',sidecar)
    row=Store(tmp_path/'private').get(out['record_id'])
    assert len(row['evidence'])==2
    assert any(e['origin']==str(sidecar.resolve()) for e in row['evidence'])

def test_readonly_mlflow_snapshot_includes_observation_time():
    from expkm.sources import MLflowSource
    def transport(method,path,body):
        if path.startswith('runs/get'):return {'run':{'info':{'run_id':'synthetic','status':'RUNNING'},'data':{}}}
        return {'files':[]}
    s=MLflowSource('http://127.0.0.1:15000',['http://127.0.0.1:15000'],transport).snapshot('synthetic')
    assert s.get('observed_at')

@pytest.mark.skipif(os.name!='nt',reason='Windows long-path behavior')
def test_windows_long_private_root_can_archive_and_verify(tmp_path):
    source=tmp_path/'input';source.mkdir();file=source/'result.json';file.write_text('{"score":0.8}')
    root=tmp_path/('long-root-'+'a'*75)/('b'*80)/('c'*55)
    store=Store(root)
    row=store.record('q','attempt',{'status':'completed'},[file],[source])
    assert store.verify(row['record_id'])['verified']
