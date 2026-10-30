"""Synthetic stage contracts; no account, remote document or experiment execution."""
import json
from pathlib import Path
import pytest
from expkm.cli import parser, run
from expkm.store import Store
from expkm.knowledge import Knowledge, render
from expkm.templates import TemplateRequired
from test_knowledge import draft


def cli(store, *args):
    return run(parser().parse_args(['--store', str(store.root), *map(str, args)]))


def select(store, command, *args):
    p = cli(store, command, 'preview', '--topic', 'quality', *args)
    return cli(store, command, 'confirm', '--topic', 'quality',
               '--proposal', p['proposal'], '--approve', p['version'])


def test_record_setup_only_asks_for_private_location_and_reuses_it(tmp_path):
    store = Store(tmp_path/'private')
    value = cli(store, 'setup', '--topic', 'quality', '--stage', 'record')
    assert [q['id'] for q in value['questions']] == ['record_location']
    assert value['introduction'].count('```text') == 1
    select(store, 'record-location')
    assert not cli(store, 'setup', '--topic', 'quality', '--stage', 'record')['questions']
    file = tmp_path/'result.json'; file.write_text('{"status":"failed","score":0}')
    r = cli(store, 'record', '--topic', 'quality', '--source-id', 'attempt',
            '--file', file, '--root', tmp_path)
    assert store.get(r['record_id'])['metadata']['status'] == 'failed'
    assert not (store.root/'templates').exists()
    assert not (store.root/'destinations').exists()


def test_record_stops_before_input_read_until_location_confirmed(tmp_path):
    store = Store(tmp_path/'private')
    from expkm.selections import SelectionRequired
    with pytest.raises(SelectionRequired):
        cli(store, 'record', '--topic', 'quality', '--source-id', 'a',
            '--file', tmp_path/'missing.json', '--root', tmp_path)


def test_analysis_only_never_demands_template_or_report_destination(tmp_path):
    store = Store(tmp_path/'private')
    f = tmp_path/'result.txt'; f.write_text('Synthetic offline evidence')
    row = store.record('quality', 'one', {'status':'completed'}, [f], [tmp_path])
    value = cli(store, 'setup', '--topic', 'quality', '--stage', 'synthesize')
    assert value['questions'] == []
    prepared = cli(store, 'synthesize', '--topic', 'quality', '--prepare')
    assert prepared['status'] == 'needs_agent_synthesis'
    state = Knowledge(store).update('quality', draft([row]))
    assert state['report_template'] is None
    with pytest.raises(TemplateRequired): render(state)
    p = store.root/'draft.json'; p.write_text(json.dumps(draft([row])))
    result = cli(store, 'synthesize', '--topic', 'quality', '--draft', p,
                 '--expected-version', state['version'])
    assert result['claims'] == 1 and result.get('preview') is None
    assert not (store.root/'destinations').exists()


def test_report_and_archive_setup_ask_different_questions(tmp_path):
    store = Store(tmp_path/'private')
    report = cli(store, 'setup', '--topic', 'quality', '--stage', 'sync')
    assert [q['id'] for q in report['questions']] == ['template','save_method','save_location']
    archive = cli(store, 'setup', '--topic', 'quality', '--stage', 'sync', '--sync-kind', 'archive')
    assert [q['id'] for q in archive['questions']] == ['archive_scope','archive_location']
    assert all(q.get('required') for q in archive['questions'])


def test_archive_only_plans_without_report_or_template(tmp_path):
    store = Store(tmp_path/'private')
    f = tmp_path/'result.txt'; f.write_text('Synthetic archival evidence')
    store.record('quality', 'one', {'status':'aborted'}, [f], [tmp_path])
    select(store, 'archive-destination', '--scope', 'full', '--wiki', 'synthetic-parent')
    result = cli(store, 'archive', 'plan', '--topic', 'quality')
    plan = json.loads(Path(result['output']).read_text(encoding='utf-8'))
    assert plan['wiki_parent'] == 'synthetic-parent' and plan['scope'] == 'full'
    assert not (store.root/'templates').exists()
    assert not cli(store, 'setup', '--topic', 'quality', '--stage', 'sync',
                   '--sync-kind', 'archive')['questions']


def test_four_discoverable_skills_share_one_core_in_release(tmp_path):
    from expkm.packaging import build_plugin
    import zipfile
    root = Path(__file__).parents[1]
    out = tmp_path/'plugin.zip'; build_plugin(root, out)
    with zipfile.ZipFile(out) as z:
        entries = z.namelist()
        names = {'post-experiment-knowledge','experiment-record','experiment-synthesize','experiment-sync'}
        assert {p.split('/')[2] for p in entries if p.endswith('/SKILL.md')} == names
        for name in names:
            metadata = z.read('post-experiment-knowledge/skills/'+name+'/agents/openai.yaml')
            assert b'allow_implicit_invocation: true' in metadata
        assert sum(p.endswith('/src/expkm/cli.py') for p in entries) == 1


def test_workflow_audit_does_not_treat_partial_work_as_complete(tmp_path):
    store = Store(tmp_path/'private')
    request = store.root/'request.json'
    request.write_text(json.dumps({'topic':'quality','stages':['record','synthesize','sync'],
                                  'source_ids':['one'], 'reports':['markdown'], 'archives':'none'}))
    value = cli(store, 'workflow', '--request', request)
    assert not value['verified'] and value['remaining'] == ['record','synthesize','report:markdown']


def test_complete_workflow_requires_both_reports_and_full_archive_readback(tmp_path, monkeypatch):
    from expkm.common import write_json
    from test_knowledge import metadata
    from test_sync import FakeDocument
    from test_archives import Drive
    import expkm.feishu as feishu
    import expkm.drive as drive_module
    store = Store(tmp_path/'private')
    select(store, 'record-location')
    rows = []
    for i in range(3):
        file = tmp_path/('run-'+str(i)+'.json'); write_json(file, metadata(.8))
        result = cli(store, 'record', '--topic', 'quality', '--source-id', 'run-'+str(i),
                     '--file', file, '--root', tmp_path)
        rows.append(store.get(result['record_id']))
    file = store.root/'draft.json'; write_json(file, draft(rows))
    knowledge = cli(store, 'synthesize', '--topic', 'quality', '--draft', file)
    select(store, 'template', '--builtin')
    select(store, 'destination', '--mode', 'both', '--target', store.root/'report.md',
           '--root', store.root, '--document', 'synthetic-doc')
    select(store, 'archive-destination', '--scope', 'full', '--folder', 'synthetic-folder')
    doc = FakeDocument(); doc.document = 'synthetic-doc'; drive = Drive()
    monkeypatch.setattr(feishu, 'LarkDocument', lambda *a, **k:doc)
    monkeypatch.setattr(drive_module, 'LarkDrive', lambda *a, **k:drive)
    preview = cli(store, 'report-preview', '--topic', 'quality')
    request = {'topic':'quality','stages':['record','synthesize','sync'],
               'source_ids':['run-'+str(i) for i in range(3)], 'reports':['markdown','feishu'],
               'archives':'full', 'knowledge_version':knowledge['version'],'report_plans':{}}
    path = store.root/'workflow.json'
    def audit():
        write_json(path, request)
        return cli(store, 'workflow', '--request', path)
    assert audit()['remaining'] == ['report:markdown','report:feishu','archive:full']
    p = cli(store, 'sync', 'plan', '--topic', 'quality', '--adapter', 'markdown',
            '--content', preview['preview'])
    request['report_plans']['markdown'] = p['output']
    assert not audit()['verified']
    cli(store, 'sync', 'apply', '--plan', p['output'], '--approve', p['plan_id'])
    replacements = store.root/'replacements.json'
    write_json(replacements, {'a':'<p>Scoped synthetic conclusion. Three records support the baseline.</p>'})
    p = cli(store, 'sync', 'plan', '--topic', 'quality', '--adapter', 'feishu',
            '--replacements', replacements)
    request['report_plans']['feishu'] = p['output']
    cli(store, 'sync', 'apply', '--plan', p['output'], '--approve', p['plan_id'], '--allow-feishu-write')
    assert audit()['remaining'] == ['archive:full']
    p = cli(store, 'archive', 'plan', '--topic', 'quality'); request['archive_plan'] = p['output']
    cli(store, 'archive', 'apply', '--plan', p['output'], '--approve', p['plan_id'], '--allow-feishu-upload')
    assert audit()['verified'] and drive.writes == 1 and doc.writes == 1
    assert (store.root/'report.md').exists()
    # Idempotence and live verification: no second write, but later edit invalidates success.
    assert audit()['verified'] and drive.writes == 1 and doc.writes == 1
    # Old verified reports cannot satisfy a newer conclusion revision.
    newer = draft(rows, text='A revised scoped interpretation.')
    newer['reason'] = 'Synthetic semantic revision.'
    state = Knowledge(store).update('quality', newer, knowledge['version'])
    request['knowledge_version'] = state['version']
    assert audit()['remaining'] == ['report:markdown','report:feishu','archive:full']
    # Restore the old audit pin to prove it also detects stale synthesis.
    request['knowledge_version'] = knowledge['version']
    assert 'synthesize' in audit()['remaining']
    request['knowledge_version'] = state['version']
    (store.root/'report.md').write_text('Concurrent user edit')
    assert 'report:markdown' in audit()['remaining']


def test_analysis_workflow_checks_evidence_bytes_not_only_refs(tmp_path):
    from expkm.common import write_json
    store = Store(tmp_path/'private'); f = tmp_path/'result.txt'; f.write_text('Synthetic evidence')
    row = store.record('quality','one',{'status':'completed'},[f],[tmp_path])
    state = Knowledge(store).update('quality',draft([row]))
    path = store.root/'request.json'
    write_json(path, {'topic':'quality','stages':['synthesize'],'source_ids':['one'],
                      'knowledge_version':state['version']})
    assert cli(store,'workflow','--request',path)['verified']
    (store.root/row['evidence'][0]['object']).write_text('Corrupt')
    assert cli(store,'workflow','--request',path)['remaining'] == ['synthesize']


def test_analysis_update_preserves_existing_filled_report_without_reasking(tmp_path):
    from test_knowledge import make_records
    store, rows = make_records(tmp_path, 1)
    value = draft(rows); value['report_sections'] = {'limitations':[{'type':'paragraph','text':'Scoped boundary.'}]}
    old = Knowledge(store).update('quality', value)
    new = Knowledge(store).update('quality', draft(rows), old['version'])
    assert new['report_sections'] == old['report_sections']


def test_stage_selections_are_cas_bound_and_cannot_be_overwritten_by_exports(tmp_path):
    from expkm.selections import Selections
    from expkm.cli import save_private
    store = Store(tmp_path/'private'); choices = Selections(store, 'archive-destination')
    p = choices.propose('quality', {'archives':{'scope':'trace','wiki':'synthetic-node'}})
    old = choices.confirm('quality', p, p['version'])
    p = choices.propose('quality', {'archives':{'scope':'full','wiki':'synthetic-node'}})
    with pytest.raises(ValueError): choices.confirm('quality', p, p['version'])
    choices.confirm('quality', p, p['version'], old['version'])
    with pytest.raises(ValueError): save_private(store, store.root/'archive-destination'/'quality'/'head.json', {})


def test_bad_optional_feishu_preference_cannot_block_local_record_setup(tmp_path, monkeypatch):
    import expkm.common as common
    private = tmp_path/'preferences'; private.mkdir()
    (private/'preferences.json').write_text('INVALID PRIVATE DATA')
    monkeypatch.setattr(common, 'private_default', lambda:private/'projects')
    result = cli(Store(tmp_path/'store'), 'setup', '--topic','quality','--stage','record')
    assert result['status'] == 'needs_setup'
    assert 'INVALID PRIVATE DATA' not in json.dumps(result)


def test_historical_audit_requires_reviewed_mapping_of_archived_source(tmp_path):
    from expkm.common import write_json
    from expkm.documents import migration_preview
    store = Store(tmp_path/'private')
    source = tmp_path/'history.txt'; source.write_text('<p id="a">Synthetic 0.8</p>')
    row = store.record('quality','history',{'status':'unknown'},[source],[tmp_path])
    request = {'topic':'quality','stages':['record'],'source_ids':['history'],
               'organization_required':True}
    path = store.root/'workflow.json'
    def audit():
        write_json(path,request)
        return cli(store,'workflow','--request',path)
    assert audit()['remaining'] == ['organization']
    preview = store.root/'migration.json'
    mapping = [{'block_id':'a','destination':'review','question':'quality','reason':'Inspect mixed facts'}]
    write_json(preview,migration_preview(source.read_text(),mapping,'# Synthetic'))
    request['organization'] = [{'record_id':row['record_id'],'revision':row['revision'],
                                'sha256':row['evidence'][0]['sha256'],'preview':str(preview)}]
    assert audit()['remaining'] == ['organization']
    mapping[0]['destination'] = 'archive'
    write_json(preview,migration_preview(source.read_text(),mapping,'# Synthetic'))
    assert audit()['verified']
