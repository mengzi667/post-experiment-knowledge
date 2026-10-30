"""Verify requested post-result deliverables; never dispatch experiments or models."""
from pathlib import Path
from .common import identifier, read_json, within
from .knowledge import Knowledge
from .templates import Templates
from .destinations import Destinations
from .selections import Selections


def check(store, request, config=None):
    from .cli import parser, run
    allowed = {'topic','stages','source_ids','reports','archives','knowledge_version',
               'report_plans','archive_plan','excluded_from_claims','organization_required','organization'}
    if not isinstance(request, dict) or set(request)-allowed:
        raise ValueError('Unknown workflow request fields')
    topic = identifier(request['topic'])
    stages = request['stages']; reports = request.get('reports', [])
    scope = request.get('archives', 'none'); sources = request.get('source_ids', [])
    if (not isinstance(stages, list) or not stages or len(set(stages)) != len(stages)
            or not set(stages) <= {'record','synthesize','sync'}
            or not isinstance(reports, list) or len(set(reports)) != len(reports)
            or not set(reports) <= {'markdown','feishu'} or scope not in {'none','trace','full'}
            or not isinstance(sources, list) or len(set(sources)) != len(sources)
            or not all(isinstance(s, str) and s for s in sources)
            or (('record' in stages or 'synthesize' in stages) and not sources)
            or ('sync' in stages and not reports and scope == 'none')
            or ('sync' not in stages and (reports or scope != 'none'))):
        raise ValueError('Describe exactly the requested stages, sources and outputs')
    rows = {r['source_key']:r for r in store.records(topic)}
    selected = [rows[s] for s in sources if s in rows]
    remaining = []
    if 'record' in stages and (len(selected) != len(sources) or not all(store.verify(r['record_id'])['verified'] for r in selected)):
        remaining.append('record')
    if request.get('organization_required'):
        from .documents import migration_preview
        from .common import digest
        entries = request.get('organization', []); ok = bool(entries)
        for entry in entries:
            row = store.get(entry['record_id'], entry['revision'])
            evidence = next((e for e in row['evidence'] if e['sha256'] == entry['sha256']), None)
            if row['topic'] != topic or evidence is None:
                raise ValueError('Historical mapping needs archived topic evidence')
            raw = within(store.root/evidence['object'], [store.root/'objects']).read_bytes()
            if digest(raw) != evidence['sha256']:
                raise ValueError('Historical source evidence changed')
            # Exact archived envelope or XML, never untrusted preview assertions.
            text = raw.decode('utf-8-sig')
            try:
                import json
                text = json.loads(text)['data']['document']['content']
            except (ValueError, TypeError, KeyError):
                pass
            preview = read_json(within(entry['preview'], [store.root]))
            rebuilt = migration_preview(text, preview['mapping'], preview['main_markdown'])
            ok = ok and rebuilt == preview and rebuilt['review_pending'] == 0
        if not ok: remaining.append('organization')
    state = Knowledge(store).head(topic)
    if 'synthesize' in stages:
        excluded = request.get('excluded_from_claims', {})
        if not isinstance(excluded, dict) or not all(isinstance(v,str) and v.strip() for v in excluded.values()):
            raise ValueError('Process-only evidence exclusions require reviewable reasons')
        refs = {(e['record_id'],e['revision']) for c in (state or {}).get('claims', [])
                if c['status'] != 'superseded' for e in c['evidence']}
        if (not state or request.get('knowledge_version') != state['version']
                or len(selected) != len(sources)
                or not all(store.verify(r['record_id'])['verified'] for r in selected)
                or not all((r['record_id'],r['revision']) in refs or r['record_id'] in excluded for r in selected)):
            remaining.append('synthesize')

    def verify(command, path):
        args = ['--store',str(store.root)]
        if config: args += ['--config',str(config)]
        args += [command,'verify','--plan',str(path)]
        return run(parser().parse_args(args)).get('verified') is True

    for adapter in reports:
        ok = False
        path = request.get('report_plans', {}).get(adapter)
        if path:
            path = within(Path(path), [store.root]); plan = read_json(path)
            binding = Destinations(store).require(topic); template = Templates(store).require(topic)
            if (plan.get('adapter') == adapter and plan.get('report_template') == {'topic':topic,'version':template['version']}
                    and plan.get('report_destination') == {'topic':topic,'version':binding['version']}
                    and ('synthesize' not in stages or (state and plan.get('report_knowledge') == {'topic':topic,'version':state['version']}))):
                # Real readback, not a trusted old success flag.
                ok = verify('sync', path)
        if not ok: remaining.append('report:'+adapter)
    if scope != 'none':
        ok = False
        path = request.get('archive_plan')
        if path:
            path = within(Path(path), [store.root]); plan = read_json(path)
            binding = Selections(store, 'archive-destination').require(topic)
            if plan.get('topic') == topic and plan.get('scope') == scope and plan.get('destination_version') == binding['version']:
                # A historical bundle must not mask missing new records/knowledge.
                from .archives import ArchiveSync
                fresh = ArchiveSync(store).plan(topic)
                if fresh['bundle_sha256'] == plan.get('bundle_sha256'):
                    ok = verify('archive', path)
        if not ok: remaining.append('archive:'+scope)
    return {'verified':not remaining, 'status':'complete' if not remaining else 'incomplete',
            'remaining':remaining, 'expected_stages':stages,
            'scope':'Artifact integrity, evidence coverage and current output readback; Agent reviews semantics and readability.'}
