import json
from pathlib import Path
import pytest
from expkm.cli import parser,run
from test_archives import project,Drive


def cli(store,*args):return run(parser().parse_args(['--store',str(store.root),*map(str,args)]))


def test_archive_cli_preview_never_uploads_and_apply_requires_opt_in(tmp_path,monkeypatch):
    store,_=project(tmp_path);drive=Drive()
    p=cli(store,'archive','plan','--topic','quality')
    assert p['upload_authorized'] is False and drive.writes==0
    with pytest.raises(ValueError):cli(store,'archive','apply','--plan',p['output'],'--approve',p['plan_id'])
    assert not (store.root/'archive-sync'/(p['plan_id']+'.json')).exists()
    import expkm.drive as adapter
    flags=[]
    def client(allowed,workspace,write_enabled=False):flags.append(write_enabled);return drive
    monkeypatch.setattr(adapter,'LarkDrive',client)
    result=cli(store,'archive','apply','--plan',p['output'],'--approve',p['plan_id'],'--allow-feishu-upload')
    assert result['verified'] and drive.writes==1 and flags==[True]
    result=cli(store,'archive','verify','--plan',p['output'])
    assert result['verified'] and flags==[True,False]
    receipt=json.loads(Path(result['receipt']).read_text(encoding='utf-8'))
    assert receipt['file_token']=='file-1'


def test_setup_cli_returns_intro_and_selection_cards(tmp_path):
    from expkm.store import Store
    store=Store(tmp_path/'private');value=cli(store,'setup','--topic','quality')
    assert value['status']=='needs_setup' and value['introduction'].index('```text')>0
    assert [q['id'] for q in value['questions']]==['template','save_method','archive_scope','save_location']

def test_cli_missing_scope_is_actionable_before_any_upload(tmp_path,monkeypatch,capsys):
    from expkm.cli import main
    from expkm.drive import FeishuPermissionError
    store,_=project(tmp_path)
    class NeedsScope(Drive):
        def preflight(self,folder):raise FeishuPermissionError(['space:document:retrieve'])
    d=NeedsScope();p=cli(store,'archive','plan','--topic','quality')
    import expkm.drive as adapter
    monkeypatch.setattr(adapter,'LarkDrive',lambda *a,**k:d)
    rc=main(['--store',str(store.root),'archive','apply','--plan',p['output'],'--approve',p['plan_id'],'--allow-feishu-upload'])
    value=json.loads(capsys.readouterr().out)
    assert rc==2 and value['status']=='needs_feishu_authorization' and value['missing_scopes']==['space:document:retrieve']
    assert d.writes==0 and not (store.root/'archive-sync'/(p['plan_id']+'.json')).exists()
