import json
import pytest
from expkm.sources import read_result, MLflowSource

@pytest.mark.parametrize('suffix,body,count',[
    ('.json','{"status":"failed","metrics":{"recall":0,"latency":null}}',1),
    ('.jsonl','{"id":1}\n{"id":2}\n',2),
    ('.csv','id,metric\na,0\nb,\n',2),
    ('.md','# Result\nNo valid metric available.',1),
    ('.txt','Interrupted before evaluation.',1),
    ('.log','SYNTHETIC_ONLY: interrupted before evaluation.\n',1),
])
def test_multiple_result_formats_are_preserved(tmp_path,suffix,body,count):
    p=tmp_path/('result'+suffix);p.write_text(body,encoding='utf-8')
    r=read_result(p)
    assert r and r['rows']==count and r['format']==suffix[1:]
    if suffix=='.json':assert r['data']['metrics']=={'recall':0,'latency':None}

def test_code_and_pickle_are_never_executed(tmp_path):
    p=tmp_path/'result.py';p.write_text('raise RuntimeError("should never execute")')
    with pytest.raises(ValueError):read_result(p)

def test_mlflow_reads_history_parent_and_business_status_separately():
    calls=[]
    def transport(method,path,body):
        calls.append((method,path))
        if path.startswith('runs/get'):
            return {'run':{'info':{'run_id':'synthetic-run','status':'RUNNING','artifact_uri':'mlflow-artifacts:/e/r/artifacts'},'data':{'tags':[{'key':'stage_status','value':'not_started'},{'key':'mlflow.parentRunId','value':'parent'}],'params':[{'key':'rank','value':'8'}],'metrics':[{'key':'score','value':0}]}}}
        if path.startswith('metrics/get-history'):return {'metrics':[{'value':0,'step':0},{'value':1,'step':1}]}
        if path.startswith('artifacts/list'):return {'files':[{'path':'summary.json','is_dir':False}]}
        raise AssertionError(path)
    client=MLflowSource('http://127.0.0.1:15000',['http://127.0.0.1:15000'],transport)
    row=client.snapshot('synthetic-run',['score'])
    assert row and row['tracking_status']=='RUNNING' and row['business_stage']=='not_started'
    assert len(row['metric_history']['score'])==2 and row['parent_run_id']=='parent'
    assert all(method=='GET' for method,path in calls)

def test_mlflow_origin_and_embedded_credentials_are_rejected():
    with pytest.raises(ValueError):MLflowSource('https://unapproved.invalid',[])
    with pytest.raises(ValueError):MLflowSource('https://user:secret@approved.invalid',['https://approved.invalid'])

def test_mlflow_lists_all_run_pages_without_writing():
    calls=[]
    def transport(method,path,body):
        calls.append((method,path,body))
        if 'page_token' not in body:return {'runs':[{'info':{'run_id':'one'}}],'next_page_token':'next'}
        return {'runs':[{'info':{'run_id':'two'}}]}
    c=MLflowSource('http://127.0.0.1:15000',['http://127.0.0.1:15000'],transport)
    assert hasattr(c,'search_runs')
    assert len(c.search_runs('experiment')['runs'])==2
    assert all(path=='runs/search' for method,path,body in calls)
