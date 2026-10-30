import json
from pathlib import Path
import pytest
from expkm.store import Store

@pytest.fixture
def material(tmp_path):
    source = tmp_path/'source'; source.mkdir()
    result = source/'results.json'; result.write_text('{"recall":0,"missing":null}', encoding='utf-8')
    return Store(tmp_path/'private'), source, result

def record(material, key='attempt-1', **extra):
    store, source, result = material
    return store.record('quality', key, {'status':'completed','config':{'rank':8},**extra}, [result], [source])

def test_evidence_is_copied_losslessly_and_same_source_is_idempotent(material):
    first = record(material); second = record(material)
    assert first and first == second
    entry = first['evidence'][0]
    assert (Path(material[0].root)/entry['object']).read_bytes() == material[2].read_bytes()
    assert material[0].verify(first['record_id'])['verified']

def test_true_repeats_with_same_config_have_distinct_identity(material):
    a=record(material,'attempt-1'); b=record(material,'attempt-2')
    assert a and b and a['record_id'] != b['record_id']
    assert len(material[0].records('quality')) == 2

def test_changed_source_creates_revision_without_erasing_first(material):
    a=record(material)
    assert a
    material[2].write_text('{"recall":0.9}',encoding='utf-8')
    b=record(material)
    assert b['record_id']==a['record_id'] and b['revision']!=a['revision']
    assert len(material[0].history(a['record_id'])) == 2
    assert material[0].get(a['record_id'], a['revision']) == a

def test_missing_evidence_does_not_create_a_partial_record(material):
    s,root,path=material
    with pytest.raises(ValueError):s.record('quality','one',{},[path,root/'absent.json'],[root])
    assert s.records()==[]

def test_outside_root_and_symlink_are_rejected(material,tmp_path):
    s,root,path=material; outside=tmp_path/'secret.txt';outside.write_text('private')
    with pytest.raises(ValueError):s.record('quality','one',{},[outside],[root])
    link=root/'alias.txt'
    try:link.symlink_to(outside)
    except OSError:return
    with pytest.raises(ValueError):s.record('quality','one',{},[link],[root])

@pytest.mark.parametrize('status',['failed','aborted','partial','unknown'])
def test_failed_and_incomplete_results_are_archivable(material,status):
    row=record(material,status=status)
    assert row and row['metadata']['status']==status

def test_sensitive_data_never_goes_to_a_project_source_directory(material):
    public=Path(__file__).parents[1]
    with pytest.raises(ValueError):Store(public/'private')

def test_tampered_evidence_is_reported(material):
    row=record(material)
    assert row
    (Path(material[0].root)/row['evidence'][0]['object']).write_bytes(b'changed')
    assert not material[0].verify(row['record_id'])['verified']

def test_index_can_be_rebuilt_from_record_revisions(material):
    row=record(material)
    assert row
    material[0].reindex()
    assert len(material[0].records())==1
    assert material[0].trace(row['record_id'])['record_id']==row['record_id']
