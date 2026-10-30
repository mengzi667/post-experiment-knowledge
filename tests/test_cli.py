import json
import os
from pathlib import Path
import subprocess
import sys

def call(*args):
    return subprocess.run([sys.executable,'-m','expkm',*map(str,args)],capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONPATH':str(Path(__file__).parents[1]/'src')})

def select_setup(store,topic):
    r=call('--store',store,'template','preview','--topic',topic,'--builtin')
    assert r.returncode==0,r.stdout+r.stderr
    p=json.loads(r.stdout)
    r=call('--store',store,'template','confirm','--topic',topic,'--proposal',p['proposal'],'--approve',p['version'])
    assert r.returncode==0,r.stdout+r.stderr
    r=call('--store',store,'destination','preview','--topic',topic,'--mode','markdown','--target',store/'report.md','--root',store,'--archive-scope','none')
    assert r.returncode==0,r.stdout+r.stderr
    p=json.loads(r.stdout)
    r=call('--store',store,'destination','confirm','--topic',topic,'--proposal',p['proposal'],'--approve',p['version'])
    assert r.returncode==0,r.stdout+r.stderr

def test_cli_records_and_previews_without_any_platform(tmp_path):
    source=tmp_path/'inputs';source.mkdir();file=source/'result.json'
    file.write_text('{"status":"completed","metrics":{"score":0.8}}')
    store=tmp_path/'private'
    select_setup(store,'quality')
    r=call('--store',store,'record','--topic','quality','--source-id','attempt-one','--file',file,'--root',source)
    assert r.returncode==0,r.stderr
    summary=json.loads(r.stdout);assert 'record_id' in summary and 'metrics' not in summary
    r=call('--store',store,'verify','--record',summary['record_id'])
    assert r.returncode==0 and json.loads(r.stdout)['verified']
    r=call('--store',store,'synthesize','--topic','quality','--prepare')
    assert r.returncode==0 and json.loads(r.stdout)['status']=='needs_agent_synthesis'

def test_cli_errors_do_not_echo_experiment_content(tmp_path):
    select_setup(tmp_path/'private','q')
    root=tmp_path/'input';root.mkdir();p=root/'result.json';p.write_text('{"private":"DO_NOT_ECHO_EXPERIMENT_PAYLOAD",BROKEN')
    r=call('--store',tmp_path/'private','record','--topic','q','--source-id','a','--file',p,'--root',root)
    assert r.returncode!=0
    assert 'DO_NOT_ECHO_EXPERIMENT_PAYLOAD' not in r.stdout+r.stderr

def test_cli_has_no_experiment_execution_commands():
    r=call('--help');assert r.returncode==0
    assert 'record' in r.stdout and 'synthesize' in r.stdout
    r=call('train');assert r.returncode!=0
