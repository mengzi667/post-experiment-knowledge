import json
import subprocess
import pytest
from expkm.feishu import LarkDocument

def test_document_must_be_explicitly_allowed(tmp_path):
    with pytest.raises(ValueError):LarkDocument('other', ['synthetic-doc'], tmp_path)

def test_default_client_cannot_write(tmp_path):
    c=LarkDocument('synthetic-doc',['synthetic-doc'],tmp_path)
    assert hasattr(c,'replace')
    with pytest.raises(ValueError):c.replace('block','<p>private</p>',1)

def test_read_preserves_full_native_xml_and_uses_only_read_command(tmp_path,monkeypatch):
    calls=[]
    def run(argv,**kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv,0,json.dumps({'ok':True,'data':{'document':{'revision_id':7,'content':'<p id="a">Evidence</p><img id="im" token="synthetic"/>','reference_map':{}}}}).encode(),b'')
    monkeypatch.setattr('subprocess.run',run)
    c=LarkDocument('synthetic-doc',['synthetic-doc'],tmp_path)
    row=c.read()
    assert row and row['revision']==7 and len(row['blocks'])==2
    assert calls[0][1:3]==['docs','+fetch'] and '--detail' in calls[0]
