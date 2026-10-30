import copy
import xml.etree.ElementTree as E
import pytest
from expkm.sync import MarkdownSync,FeishuSync,SyncConflict

def test_markdown_preserves_manual_text_and_repeated_apply_is_noop(tmp_path):
    target=tmp_path/'report.md';target.write_text('# Manual\nKeep this.\n',encoding='utf-8')
    s=MarkdownSync(tmp_path/'private')
    plan=s.plan(target,'## Finding\nBaseline retained.',[tmp_path])
    assert plan
    with pytest.raises(ValueError):s.apply(plan,'not-approved')
    s.apply(plan,plan['plan_id']);s.apply(plan,plan['plan_id'])
    text=target.read_text();assert text.startswith('# Manual\nKeep this.') and text.count('Baseline retained.')==1
    assert s.verify(plan)['verified']
    s.rollback(plan,plan['plan_id'])
    assert target.read_text()=='# Manual\nKeep this.\n'

def test_markdown_concurrent_edit_is_not_overwritten(tmp_path):
    target=tmp_path/'report.md';target.write_text('Original')
    s=MarkdownSync(tmp_path/'private');p=s.plan(target,'New',[tmp_path]);assert p
    target.write_text('Another author')
    with pytest.raises(SyncConflict):s.apply(p,p['plan_id'])
    assert target.read_text()=='Another author'

class FakeDocument:
    def __init__(self):
        self.revision=1;self.writes=0;self.fail_after_write=False
        self.blocks=['<p id="a">Old conclusion</p>','<p id="b"><cite type="doc" doc-id="synthetic-ref"/>Unchanged</p>','<table id="t"><tbody><tr><td><p>1</p></td></tr></tbody></table>']
    def read(self):return {'revision':self.revision,'blocks':list(self.blocks)}
    def replace(self,block_id,xml,revision):
        if revision!=self.revision:raise SyncConflict('revision')
        i=next(i for i,b in enumerate(self.blocks) if E.fromstring(b).get('id')==block_id)
        n=E.fromstring(xml);n.set('id','new-'+str(self.writes));self.blocks[i]=E.tostring(n,encoding='unicode');self.revision+=1;self.writes+=1
        if self.fail_after_write:self.fail_after_write=False;raise TimeoutError('unknown result')

def test_feishu_minimal_write_preserves_native_refs_and_tables(tmp_path):
    client=FakeDocument();s=FeishuSync(client,tmp_path/'private')
    p=s.plan({'a':'<p>New conclusion</p>'});assert p
    s.apply(p,p['plan_id']);s.apply(p,p['plan_id'])
    assert client.writes==1 and client.blocks[1].find('synthetic-ref')>0
    assert '<td><p>1</p></td>' in client.blocks[2]
    assert s.verify(p)['verified']

def test_unknown_write_is_reconciled_without_replay(tmp_path):
    client=FakeDocument();s=FeishuSync(client,tmp_path/'private')
    p=s.plan({'a':'<p>Updated</p>','t':'<table><tbody><tr><td><p>2</p></td></tr></tbody></table>'});assert p
    client.fail_after_write=True
    with pytest.raises(TimeoutError):s.apply(p,p['plan_id'])
    s.apply(p,p['plan_id'])
    assert client.writes==2 and s.verify(p)['verified']
    s.rollback(p,p['plan_id'])
    assert 'Old conclusion' in client.blocks[0] and '<p>1</p>' in client.blocks[2]

def test_feishu_concurrent_edit_stops_and_no_silent_resource_removal(tmp_path):
    client=FakeDocument();s=FeishuSync(client,tmp_path/'private')
    p=s.plan({'a':'<p>Updated</p>'});assert p
    client.blocks[2]='<p id="t">Other author</p>'
    with pytest.raises(SyncConflict):s.apply(p,p['plan_id'])
    assert client.writes==0
    with pytest.raises(ValueError):s.plan({'b':'<p>Removed reference</p>'})
