import json
import subprocess
from pathlib import Path
import pytest
from expkm.common import digest,write_json
from expkm.destinations import Destinations
from expkm.archives import ArchiveSync
from expkm.drive import LarkDrive
from expkm.onboarding import setup_status
from test_archives import project,Drive


def wiki_project(tmp_path):
    store,rows=project(tmp_path);d=Destinations(store);old=d.require('quality');definition=old['definition']
    definition['archives']={'scope':'full','wiki':'synthetic-wiki-parent'}
    proposal=d.propose('quality',definition);d.confirm('quality',proposal,proposal['version'],old['version'])
    return store,rows


def test_wiki_policy_has_a_distinct_target_and_rejects_mixed_locations(tmp_path):
    store,_=wiki_project(tmp_path);d=Destinations(store);definition=d.require('quality')['definition']
    assert definition['archives']=={'scope':'full','wiki':'synthetic-wiki-parent'}
    definition['archives']['folder']='synthetic-folder'
    with pytest.raises(ValueError):d.propose('quality',definition)


def test_wiki_archive_plan_and_verification_keep_target_type(tmp_path):
    store,_=wiki_project(tmp_path);drive=Drive();s=ArchiveSync(store,drive);p=s.plan('quality')
    assert p['wiki_parent']=='synthetic-wiki-parent' and 'folder' not in p
    assert s.apply(p,p['plan_id'])['verified'] and drive.writes==1


def test_adopt_existing_verified_archive_does_not_upload_again(tmp_path):
    store,_=wiki_project(tmp_path);drive=Drive();s=ArchiveSync(store,drive);p=s.plan('quality')
    drive.files['existing-file']=((store.root/p['bundle']).read_bytes(),p['wiki_parent'],p['name'])
    assert s.adopt(p,p['plan_id'],'existing-file')['verified'] and drive.writes==0
    assert s.verify(p)['verified'] and s.apply(p,p['plan_id'])['verified'] and drive.writes==0


def test_adoption_rejects_wrong_parent_or_bytes_without_acknowledging(tmp_path):
    store,_=wiki_project(tmp_path);drive=Drive();s=ArchiveSync(store,drive);p=s.plan('quality')
    drive.files['existing-file']=(b'wrong',p['wiki_parent'],p['name'])
    with pytest.raises(ValueError):s.adopt(p,p['plan_id'],'existing-file')
    assert not s._state_file(p).exists() and drive.writes==0


def test_wiki_transport_uses_wiki_parent_metadata_and_exact_download_hash(tmp_path):
    raw=b'synthetic zip';file=tmp_path/(digest(raw)+'.zip');file.write_bytes(raw);calls=[]
    def runner(argv,**kwargs):
        calls.append(argv)
        if '+node-get' in argv:
            token=argv[argv.index('--node-token')+1]
            data={'node_token':'synthetic-wiki-parent','obj_token':'container','obj_type':'docx'} if token=='synthetic-wiki-parent' else {'node_token':'synthetic-file-node','obj_token':'synthetic-file','obj_type':'file','title':'archive.zip','parent_node_token':'synthetic-wiki-parent'}
        elif '+upload' in argv:
            assert '--wiki-token' in argv and '--folder-token' not in argv;data={'file_token':'synthetic-file'}
        else:
            assert '+download' in argv
            (Path(kwargs['cwd'])/'bundle.zip').write_bytes(raw);data={}
        return subprocess.CompletedProcess(argv,0,json.dumps({'ok':True,'identity':'user','data':data}).encode(),b'')
    c=LarkDrive(['synthetic-wiki-parent'],tmp_path/'private',True,runner=runner,target_kind='wiki')
    c.preflight('synthetic-wiki-parent')
    assert c.upload(file,'synthetic-wiki-parent','archive.zip')=='synthetic-file'
    result=c.verify('synthetic-file','synthetic-wiki-parent','archive.zip',digest(raw),len(raw))
    assert result['verified'] and result['wiki_node_token']=='synthetic-file-node' and result['parent_confirmed']
    assert not any('list' in argv for argv in calls)


def test_setup_exposes_only_private_confirmed_personal_space_default(tmp_path,monkeypatch):
    import expkm.common as common
    base=tmp_path/'user-private';base.mkdir();monkeypatch.setattr(common,'private_default',lambda:base/'projects')
    pref={'personal_space':{'url':'https://tenant.invalid/wiki/synthetic-parent','node_token':'synthetic-parent','confirmed_by_user':True}}
    write_json(base/'preferences.json',pref)
    from expkm.store import Store
    value=setup_status(Store(tmp_path/'project'),'quality')
    assert value['default_personal_space']==pref['personal_space']
    assert [q['id'] for q in value['questions']]==['outcome']


def test_cli_wiki_selection_and_adoption_are_read_only(tmp_path,monkeypatch):
    from expkm.cli import parser,run
    store,_=project(tmp_path);d=Destinations(store);old=d.require('quality')
    def cli(*args):return run(parser().parse_args(['--store',str(store.root),*map(str,args)]))
    p=cli('destination','preview','--topic','quality','--mode','feishu','--document','synthetic-doc','--archive-scope','full','--archive-wiki','synthetic-wiki-parent')
    cli('destination','confirm','--topic','quality','--proposal',p['proposal'],'--approve',p['version'],'--expected-version',old['version'])
    summary=cli('archive','plan','--topic','quality');plan=json.loads(Path(summary['output']).read_text(encoding='utf-8'))
    d=Drive();d.files['existing-file']=((store.root/plan['bundle']).read_bytes(),plan['wiki_parent'],plan['name'])
    import expkm.drive as module
    calls=[]
    def adapter(allowed,workspace,write_enabled=False,**kwargs):calls.append((write_enabled,kwargs.get('target_kind')));return d
    monkeypatch.setattr(module,'LarkDrive',adapter)
    assert cli('archive','adopt','--plan',summary['output'],'--approve',summary['plan_id'],'--file-token','existing-file')['verified']
    assert calls==[(False,'wiki')] and d.writes==0
