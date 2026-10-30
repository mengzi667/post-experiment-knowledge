import io
import json
import zipfile
import pytest
from expkm.store import Store
from expkm.common import digest,write_json
from expkm.templates import Templates,default_template
from expkm.destinations import Destinations
from expkm.knowledge import Knowledge
from expkm.archives import ArchiveSync
from expkm.onboarding import setup_status
from test_knowledge import metadata,draft


class Drive:
    def __init__(self):self.files={};self.writes=0;self.fail_read=False
    def upload(self,path,folder,name):
        self.writes+=1;token='file-'+str(self.writes)
        self.files[token]=(path.read_bytes(),folder,name)
        return token
    def verify(self,token,folder,name,sha,size):
        if self.fail_read:raise TimeoutError('Unavailable readback')
        raw,f,n=self.files[token]
        return {'verified':f==folder and n==name and digest(raw)==sha and len(raw)==size,'file_token':token,'sha256':digest(raw),'bytes':len(raw)}


def project(tmp_path,scope='full',count=2):
    store=Store(tmp_path/'private');source=tmp_path/'input';source.mkdir();file=source/'result.json';file.write_text('{"score":0.8}')
    t=Templates(store);p=t.propose('quality',default_template(),'synthetic-template');t.confirm('quality',p,p['version'])
    d=Destinations(store);definition={'mode':'feishu','feishu':{'document':'synthetic-doc'},'archives':{'scope':scope}}
    if scope!='none':definition['archives']['folder']='synthetic-folder'
    p=d.propose('quality',definition);d.confirm('quality',p,p['version'])
    rows=[store.record('quality',f'attempt-{i}',metadata(),[file],[source]) for i in range(count)]
    Knowledge(store).update('quality',draft(rows))
    write_json(store.root/'private-adapter-config.json',{'excluded_canary':'NEVER_UPLOAD_ADAPTER_CONFIGURATION'})
    return store,rows


def contents(store,p):
    assert p
    return zipfile.ZipFile(io.BytesIO((store.root/p['bundle']).read_bytes()))


def test_full_bundle_preserves_all_runs_and_trace_without_adapter_config(tmp_path):
    store,rows=project(tmp_path,count=30);p=ArchiveSync(store).plan('quality');assert p
    with contents(store,p) as z:
        names=z.namelist()
        assert sum(n.startswith('records/') for n in names)==30
        assert any(n.startswith('knowledge/') for n in names) and 'experiment-index.md' in names
        assert 'manifest.json' in names and any(n.startswith('objects/') for n in names)
        assert not any('config' in n or n.startswith('destinations/') for n in names)
        assert all(b'NEVER_UPLOAD_ADAPTER_CONFIGURATION' not in z.read(n) for n in names)
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['scope']=='full'
        for e in manifest['entries']:
            assert digest(z.read(e['path']))==e['sha256']
        for row in rows:
            assert z.read(row['evidence'][0]['object'])==b'{"score":0.8}'


def test_trace_only_excludes_raw_objects_but_retains_versions_and_links(tmp_path):
    store,rows=project(tmp_path,'trace');p=ArchiveSync(store).plan('quality');assert p
    with contents(store,p) as z:
        assert not any(n.startswith('objects/') for n in z.namelist())
        row=json.loads(z.read(f"records/{rows[0]['record_id']}/{rows[0]['revision']}.json"))
        assert row['evidence'][0]['sha256']==rows[0]['evidence'][0]['sha256']
        assert json.loads(z.read('manifest.json'))['raw_evidence_included'] is False


def test_no_upload_scope_cannot_be_widened_by_archive_command(tmp_path):
    store,_=project(tmp_path,'none')
    with pytest.raises(ValueError):ArchiveSync(store).plan('quality')


def test_upload_verifies_bytes_and_repeat_apply_does_not_upload_again(tmp_path):
    store,_=project(tmp_path);drive=Drive();sync=ArchiveSync(store,drive);p=sync.plan('quality');assert p
    assert drive.writes==0
    with pytest.raises(ValueError):sync.apply(p,'not-approved')
    result=sync.apply(p,p['plan_id']);assert result and result['verified']
    assert sync.apply(p,p['plan_id'])['verified'] and drive.writes==1
    token=result['file_token'];raw,f,n=drive.files[token];drive.files[token]=(b'changed',f,n)
    assert sync.verify(p)['verified'] is False


def test_unknown_upload_is_not_blindly_repeated_and_can_reconcile(tmp_path):
    class Unknown(Drive):
        def upload(self,*args):
            super().upload(*args);raise TimeoutError('Unknown write result')
    store,_=project(tmp_path);drive=Unknown();s=ArchiveSync(store,drive);p=s.plan('quality');assert p
    with pytest.raises(TimeoutError):s.apply(p,p['plan_id'])
    with pytest.raises(TimeoutError):s.apply(p,p['plan_id'])
    assert drive.writes==1
    assert s.reconcile(p,p['plan_id'],'file-1')['verified']
    assert s.apply(p,p['plan_id'])['verified'] and drive.writes==1


def test_failed_readback_keeps_known_token_and_does_not_repeat_upload(tmp_path):
    store,_=project(tmp_path);d=Drive();s=ArchiveSync(store,d);p=s.plan('quality');assert p
    d.fail_read=True
    with pytest.raises(TimeoutError):s.apply(p,p['plan_id'])
    d.fail_read=False
    assert s.apply(p,p['plan_id'])['verified'] and d.writes==1


def test_tampering_limits_and_obvious_credentials_block_before_upload(tmp_path):
    store,rows=project(tmp_path);s=ArchiveSync(store,Drive())
    with pytest.raises(ValueError):s.plan('quality',max_bytes=1)
    p=s.plan('quality');assert p
    (store.root/p['bundle']).write_bytes(b'tampered')
    with pytest.raises(ValueError):s.apply(p,p['plan_id'])
    file=store.root/'synthetic-secret.txt';file.write_text('api_key=SYNTHETIC_SECRET_DO_NOT_UPLOAD')
    store.record('quality','sensitive',metadata(),[file],[store.root])
    with pytest.raises(ValueError):s.plan('quality')
    assert s.client.writes==0


def test_destination_change_blocks_upload_but_historical_verification_survives(tmp_path):
    store,_=project(tmp_path);d=Drive();s=ArchiveSync(store,d);p=s.plan('quality');assert p
    assert s.apply(p,p['plan_id'])['verified']
    selections=Destinations(store);old=selections.require('quality');new=old['definition'];new['archives']['folder']='other-folder'
    proposal=selections.propose('quality',new);selections.confirm('quality',proposal,proposal['version'],old['version'])
    with pytest.raises(ValueError):s.apply(p,p['plan_id'])
    assert s.verify(p)['verified'] and d.writes==1


def test_intro_has_text_tree_before_option_questions_and_reuses_confirmed_choices(tmp_path):
    store=Store(tmp_path/'private');status=setup_status(store,'quality','sync','both');assert status
    assert '```text\n' in status['introduction'] and '专题主报告' in status['introduction'] and '追溯' in status['introduction']
    assert {q['id'] for q in status['questions']}=={'template','save_method','save_location','archive_scope','archive_location'}
    assert all(2<=len(q['options'])<=3 for q in status['questions'] if 'options' in q)
    ready,_=project(tmp_path/'ready');value=setup_status(ready,'quality','sync','both');assert value
    assert value['questions']==[] and value['status']=='ready'


def test_full_archive_retains_failed_revision_and_superseded_knowledge(tmp_path):
    store,rows=project(tmp_path);file=tmp_path/'input'/'result.json';file.write_text('{"score":0.9}')
    meta=metadata(.9);meta['status']='partial'
    revised=store.record('quality',rows[0]['source_key'],meta,[file],[file.parent])
    knowledge=Knowledge(store);old=knowledge.head('quality')
    new=draft([revised,rows[1]],text='Partial follow-up evidence remains provisional.');new['reason']='A partial revision was recorded.'
    knowledge.update('quality',new,old['version'])
    p=ArchiveSync(store).plan('quality');assert p
    with contents(store,p) as z:
        m=json.loads(z.read('manifest.json'))
        assert m['record_revisions']==3 and m['knowledge_versions']==2
        assert f"records/{rows[0]['record_id']}/{rows[0]['revision']}.json" in z.namelist()
        assert f"records/{revised['record_id']}/{revised['revision']}.json" in z.namelist()
        assert z.read(revised['evidence'][0]['object'])==b'{"score":0.9}'

def test_archive_permission_preflight_stops_before_upload_or_pending_journal(tmp_path):
    class NeedsReadPermission(Drive):
        def preflight(self,folder):raise ValueError('Directory read permission missing')
    store,_=project(tmp_path);d=NeedsReadPermission();s=ArchiveSync(store,d);p=s.plan('quality')
    with pytest.raises(ValueError):s.apply(p,p['plan_id'])
    assert d.writes==0 and not s._state_file(p).exists()
