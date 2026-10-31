"""Synthetic CLI regression: archival is independent of structured extraction."""
import json
import pytest
from expkm.cli import parser, run
from expkm.common import canonical
from expkm.store import Store
from expkm.archives import ArchiveSync
from expkm.selections import Selections
from expkm.sources import read_result
from test_intake import preferences,confirm,request

def invoke(tmp_path,body,suffix,mode='auto',sidecar=None):
    store=Store(tmp_path/'private');preferences(store)
    sid=confirm(store,request(store,stages=['record']))['version']
    file=tmp_path/('input'+suffix);file.write_bytes(body)
    args=['--store',str(store.root),'--intake',sid,'record','--topic','quality',
          '--source-id','one','--file',str(file),'--root',str(tmp_path),'--source-mode',mode]
    if sidecar is not None:
        meta=tmp_path/'metadata.json';meta.write_bytes(sidecar);args+=['--metadata',str(meta)]
    value=run(parser().parse_args(args));row=store.get(value['record_id'])
    assert store.verify(row['record_id'])['verified']
    assert file.read_bytes()==body
    assert any((store.root/e['object']).read_bytes()==body for e in row['evidence'])
    return store,row,value

@pytest.mark.parametrize('suffix,body,reason',[
    ('.py',b'raise RuntimeError("MUST NEVER EXECUTE")\n','unparsed_format'),
    ('.bin',b'\x00\xff\x80SYNTHETIC_ONLY','unparsed_format'),
    ('.jsonl',b'{"score":NaN}\n{"score":Infinity}\n','nonfinite_number'),
    ('.json',b'{"score":1e999}','nonfinite_number'),
    ('.json',b'{"unfinished":','invalid_structure'),
    ('.log',b'\xff\xfeSYNTHETIC_ONLY','non_utf8'),
])
def test_auto_archives_exact_bytes_without_inventing_metrics(tmp_path,suffix,body,reason):
    _,row,result=invoke(tmp_path,body,suffix)
    source=result['sources'][0]
    assert source['extraction']=='raw_only' and source['reason']==reason
    assert row['metadata']['status']=='unknown' and 'metrics' not in row['metadata']
    assert row['metadata']['source_files'][0]['sha256']==source['sha256']
    canonical(row['metadata'])

def test_raw_mode_never_executes_selected_source(tmp_path):
    marker=tmp_path/'executed'
    body=('from pathlib import Path\nPath('+repr(str(marker))+').write_text("bad")\n').encode()
    invoke(tmp_path,body,'.py',mode='raw');assert not marker.exists()

def test_strict_mode_and_metadata_stay_finite(tmp_path):
    with pytest.raises(ValueError):invoke(tmp_path,b'{"score":NaN}','.json',mode='structured')
    with pytest.raises(ValueError):invoke(tmp_path,b'raw','.bin',sidecar=b'{"status":"completed","metrics":{"score":NaN}}')

def test_finite_structured_results_still_extract_metadata(tmp_path):
    _,row,result=invoke(tmp_path,b'{"status":"failed","metrics":{"score":0,"latency":null}}','.json')
    assert row['metadata']['metrics']=={'score':0,'latency':None}
    assert result['sources'][0]['extraction']=='structured'

def test_raw_local_archival_does_not_disable_export_secret_guard(tmp_path):
    store,_,_=invoke(tmp_path,b'password = "private-service-token"\n','.py')
    choice=Selections(store,'archive-destination');p=choice.propose('quality',{'archives':{'scope':'full','folder':'synthetic-folder'}})
    choice.confirm('quality',p,p['version'])
    with pytest.raises(ValueError,match='credential'):ArchiveSync(store).plan('quality')

def test_auto_does_not_silently_normalize_invalid_numbers(tmp_path):
    f=tmp_path/'input.jsonl';f.write_bytes(b'{"score":NaN}\n')
    value=read_result(f,mode='auto')
    assert value['data'] is None and value['rows'] is None
    assert value['reason']=='nonfinite_number' and f.read_bytes()==b'{"score":NaN}\n'
