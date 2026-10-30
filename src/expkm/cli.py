"""Post-result commands only. Normal stdout never includes raw experimental content."""
import argparse
import json
from pathlib import Path
from .common import private_default, read_json, within, write_json, atomic_bytes, output_path
from .store import Store
from .sources import read_result, MLflowSource
from .knowledge import Knowledge, compare, render
from .documents import inventory, migration_preview
from .sync import MarkdownSync, FeishuSync, sealed, authorize, validate_template_ref
from .templates import Templates, TemplateRequired, default_template, sections
from .destinations import Destinations, DestinationRequired, DestinationTargetRequired
from .archives import ArchiveSync, archive_target
from .onboarding import setup_status
from .drive import FeishuPermissionError
from .selections import Selections, SelectionRequired
from .intake import Intakes, IntakeRequired

def parser():
    p = argparse.ArgumentParser(prog='expkm', description='Record / Synthesize / Sync already-produced results; no experiment execution.')
    p.add_argument('--store', type=Path, default=private_default()/'default')
    p.add_argument('--config', type=Path, help='Private adapter configuration, outside the plugin package')
    p.add_argument('--intake', help='Explicit confirmed request version; never inferred from old preferences')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor'); sub.add_parser('reindex')
    intake = sub.add_parser('intake'); intake.add_argument('operation', choices=['preview','confirm','show','close'])
    intake.add_argument('--file', type=Path); intake.add_argument('--proposal', type=Path)
    intake.add_argument('--approve'); intake.add_argument('--version')
    setup = sub.add_parser('setup'); setup.add_argument('--topic', required=True)
    setup.add_argument('--stage', choices=['workflow','record','synthesize','sync'], default='workflow')
    setup.add_argument('--sync-kind', choices=['report','archive','both'], default='report')
    workflow = sub.add_parser('workflow'); workflow.add_argument('--request', type=Path, required=True)
    for name in ['record-location', 'archive-destination']:
        choice = sub.add_parser(name); choice.add_argument('operation', choices=['preview','confirm','show'])
        choice.add_argument('--topic', required=True); choice.add_argument('--proposal', type=Path)
        choice.add_argument('--approve'); choice.add_argument('--expected-version')
        if name == 'archive-destination':
            choice.add_argument('--scope', choices=['none','trace','full'])
            parent = choice.add_mutually_exclusive_group()
            parent.add_argument('--wiki'); parent.add_argument('--folder')
    template = sub.add_parser('template'); template.add_argument('operation', choices=['preview', 'confirm', 'show'])
    template.add_argument('--topic', required=True)
    selection = template.add_mutually_exclusive_group()
    selection.add_argument('--builtin', action='store_true'); selection.add_argument('--file', type=Path)
    template.add_argument('--source', help='Private template source/version description')
    template.add_argument('--proposal', type=Path); template.add_argument('--approve'); template.add_argument('--expected-version')
    destination = sub.add_parser('destination'); destination.add_argument('operation', choices=['preview', 'confirm', 'show'])
    destination.add_argument('--topic', required=True); destination.add_argument('--mode', choices=['markdown', 'feishu', 'both'])
    destination.add_argument('--target', type=Path); destination.add_argument('--root', type=Path); destination.add_argument('--document')
    destination.add_argument('--archive-scope', choices=['none', 'trace', 'full'])
    archive_location = destination.add_mutually_exclusive_group()
    archive_location.add_argument('--archive-folder'); archive_location.add_argument('--archive-wiki')
    destination.add_argument('--proposal', type=Path); destination.add_argument('--approve'); destination.add_argument('--expected-version')
    r = sub.add_parser('record'); r.add_argument('--topic', required=True); r.add_argument('--source-id', required=True)
    r.add_argument('--file', type=Path, action='append', required=True); r.add_argument('--root', type=Path, action='append', required=True)
    r.add_argument('--metadata', type=Path)
    m = sub.add_parser('capture-mlflow'); m.add_argument('--topic', required=True); m.add_argument('--run', required=True)
    m.add_argument('--history-key', action='append', default=[]); m.add_argument('--artifact', action='append', default=[])
    s = sub.add_parser('synthesize'); s.add_argument('--topic', required=True); s.add_argument('--prepare', action='store_true')
    s.add_argument('--draft', type=Path); s.add_argument('--expected-version'); s.add_argument('--out', type=Path)
    report = sub.add_parser('report-preview'); report.add_argument('--topic', required=True)
    report.add_argument('--sections', type=Path); report.add_argument('--out', type=Path)
    recommendation=sub.add_parser('template-context');recommendation.add_argument('--topic',required=True)
    recommendation.add_argument('--file',type=Path,action='append',required=True)
    recommendation.add_argument('--max-bytes',type=int,default=1_000_000)
    recommendation.add_argument('--out',type=Path)
    c = sub.add_parser('compare'); c.add_argument('--left', required=True); c.add_argument('--right', required=True); c.add_argument('--metric', required=True)
    c.add_argument('--changed-variable', action='append', default=[]); c.add_argument('--out', type=Path)
    o = sub.add_parser('organize'); o.add_argument('--topic', required=True); o.add_argument('--input', type=Path, required=True); o.add_argument('--mapping', type=Path)
    o.add_argument('--main', type=Path); o.add_argument('--out', type=Path, required=True)
    t = sub.add_parser('trace'); t.add_argument('--record'); t.add_argument('--topic'); t.add_argument('--claim'); t.add_argument('--out', type=Path, required=True)
    v = sub.add_parser('verify'); v.add_argument('--record', required=True)
    sync = sub.add_parser('sync'); sync.add_argument('operation', choices=['plan', 'apply', 'verify', 'rollback', 'resolve-unknown'])
    sync.add_argument('--adapter', choices=['markdown', 'feishu']); sync.add_argument('--target')
    sync.add_argument('--content', type=Path); sync.add_argument('--root', type=Path, action='append', default=[])
    sync.add_argument('--replacements', type=Path); sync.add_argument('--plan', type=Path); sync.add_argument('--out', type=Path)
    sync.add_argument('--approve'); sync.add_argument('--allow-feishu-write', action='store_true')
    sync.add_argument('--confirm-not-applied', action='store_true', help='Operator has independently confirmed the pending write was not applied')
    sync.add_argument('--topic', help='Required for a new report update plan')
    archive = sub.add_parser('archive'); archive.add_argument('operation', choices=['plan', 'apply', 'verify', 'reconcile', 'adopt', 'resolve-unknown'])
    archive.add_argument('--topic'); archive.add_argument('--plan', type=Path); archive.add_argument('--out', type=Path)
    archive.add_argument('--max-bytes', type=int); archive.add_argument('--approve'); archive.add_argument('--file-token')
    archive.add_argument('--allow-feishu-upload', action='store_true'); archive.add_argument('--confirm-not-uploaded', action='store_true')
    return p

def save_private(store, path, data, text=False):
    path = output_path(path, store.root)
    if text:
        atomic_bytes(path, data.encode('utf-8'))
    else:
        write_json(path, data)
    return str(path)

def run(args):
    store = Store(args.store)
    templates = Templates(store)
    destinations = Destinations(store)
    if args.command == 'intake':
        selections=Intakes(store)
        if args.operation == 'preview':
            if args.file is None:raise ValueError('Request metadata file required')
            proposal=selections.propose(read_json(args.file))
            path=save_private(store,store.root/'intake-previews'/(proposal['version']+'.json'),proposal)
            return {'status':'needs_request_confirmation','version':proposal['version'],'proposal':path,'execution_allowed':False}
        if args.operation == 'confirm':
            if args.proposal is None:raise ValueError('Reviewed request proposal required')
            value=selections.confirm(read_json(args.proposal),args.approve)
            return {'status':'request_confirmed','version':value['version'],'execution_allowed':True,
                    'confirmation_scope':'Explicit CLI confirmation only; not proof of UI exposure or human identity'}
        if args.operation == 'close':
            return selections.close(args.version)
        if args.version is None:raise IntakeRequired('Select this request explicitly')
        file=store.root/'intake'/'confirmed'/(args.version+'.json')
        from .common import identifier
        identifier(args.version)
        value=read_json(file)
        return {'version':value['version'],'request_file':str(file),
                'closed':(store.root/'intake'/'closed'/(args.version+'.json')).exists()}
    if args.command == 'setup':
        return setup_status(store, args.topic, args.stage, args.sync_kind, args.intake)
    if args.command == 'workflow':
        from .workflow import check
        request=read_json(args.request)
        if args.intake is not None:
            from .common import identifier
            identifier(args.intake)
            confirmed=read_json(store.root/'intake'/'confirmed'/(args.intake+'.json'))
            definition=Intakes(store).require(args.intake,confirmed['definition']['stages'][0])['definition']
            if (definition['phase']!='execution' or request.get('topic')!=definition['topic']
                    or set(request.get('stages',[]))!=set(definition['stages'])
                    or set(request.get('reports',[]))!=set(definition['reports'])
                    or request.get('archives','none')!=definition['archives']):
                raise IntakeRequired('Audit cannot omit a requested stage or output','scope_mismatch')
            if (definition['all_topic_records'] and set(definition['stages']) & {'record','synthesize'}
                    and set(request.get('source_ids',[]))!={r['source_key'] for r in store.records(definition['topic'])}):
                raise IntakeRequired('All-topic audit cannot omit existing source records','scope_mismatch')
        return check(store,request,args.config)
    if args.command in {'record-location','archive-destination'}:
        choices = Selections(store, args.command)
        if args.operation == 'preview':
            from .common import display_path
            if args.command == 'record-location':
                definition = {'store':display_path(store.root)}
            else:
                policy = {'scope':args.scope}
                if args.wiki is not None: policy['wiki'] = args.wiki
                if args.folder is not None: policy['folder'] = args.folder
                definition = {'archives':policy}
            proposal = choices.propose(args.topic, definition)
            path = save_private(store, store.root/'selection-previews'/(proposal['version']+'.json'), proposal)
            return {'status':'needs_selection_confirmation','version':proposal['version'],'proposal':path,'write_authorized':False}
        if args.operation == 'confirm':
            if args.proposal is None: raise ValueError('A reviewed selection is required')
            value = choices.confirm(args.topic, read_json(args.proposal), args.approve, args.expected_version)
        else:
            value = choices.require(args.topic)
        return {'status':'selection_confirmed','version':value['version'],'write_authorized':False}
    if args.command == 'destination':
        if args.operation == 'preview':
            if args.mode is None:
                raise ValueError('Explicitly choose a report save method')
            scope = args.archive_scope or 'none'
            definition = {'mode': args.mode, 'archives': {'scope': scope}}
            if scope != 'none':
                location = 'wiki' if args.archive_wiki is not None else 'folder'
                definition['archives'][location] = args.archive_wiki if location == 'wiki' else args.archive_folder
            elif args.archive_folder is not None or args.archive_wiki is not None:
                raise ValueError('An archive location was supplied while uploads were declined')
            if args.mode in {'markdown', 'both'}:
                if args.target is None or args.root is None:
                    raise ValueError('A Markdown filename and authorized directory are required')
                definition['markdown'] = {'target': str(args.target), 'root': str(args.root)}
            elif args.target is not None or args.root is not None:
                raise ValueError('Markdown location supplied for a different save method')
            if args.mode in {'feishu', 'both'}:
                definition['feishu'] = {'document': args.document}
            elif args.document is not None:
                raise ValueError('Feishu location supplied for a different save method')
            proposal = destinations.propose(args.topic, definition)
            output = save_private(store, store.root/'destination-previews'/(proposal['version']+'.json'), proposal)
            return {'status': 'needs_destination_confirmation', 'mode': args.mode, 'version': proposal['version'], 'proposal': output,
                    'write_authorized': False}
        if args.operation == 'confirm':
            if args.proposal is None:
                raise ValueError('A reviewed destination proposal is required')
            value = destinations.confirm(args.topic, read_json(args.proposal), args.approve, args.expected_version)
            return {'status': 'destination_confirmed', 'version': value['version'], 'mode': value['definition']['mode'], 'write_authorized': False}
        value = destinations.require(args.topic)
        return {'status': 'destination_confirmed', 'version': value['version'], 'mode': value['definition']['mode'],
                'binding': str(store.root/'destinations'/args.topic/(value['version']+'.json'))}
    if args.command == 'template':
        if args.operation == 'preview':
            if not args.builtin and not args.file:
                raise ValueError('Select a supplied template or explicitly propose the built-in template')
            if args.file and not args.source:
                raise ValueError('Describe the supplied template source and revision')
            proposal = templates.propose(args.topic, default_template() if args.builtin else read_json(args.file), args.source or 'optional-builtin-v1')
            output = save_private(store, store.root/'template-previews'/(proposal['version']+'.json'), proposal)
            return {'status': 'needs_template_confirmation', 'version': proposal['version'], 'proposal': output,
                    'headings': [n['title'] for n in sections(proposal['definition']) if n['title']]}
        if args.operation == 'confirm':
            if not args.proposal:
                raise ValueError('A reviewed template proposal is required')
            value = templates.confirm(args.topic, read_json(args.proposal), args.approve, args.expected_version)
            return {'status': 'template_confirmed', 'version': value['version']}
        value = templates.require(args.topic)
        return {'status': 'template_confirmed', 'version': value['version'], 'name': value['definition']['name'],
                'binding': str(store.root/'templates'/args.topic/(value['version']+'.json'))}
    active=None
    stage_map={'record':'record','capture-mlflow':'record','synthesize':'synthesize',
               'compare':'synthesize','organize':'synthesize','report-preview':'sync',
               'trace':'record','reindex':'record','template-context':'recommend-template'}
    operation=getattr(args,'operation',None)
    stage=stage_map.get(args.command)
    if args.command in {'sync','archive'} and operation not in {'verify'}:
        stage='sync'
    if stage:
        active=Intakes(store).require(args.intake,stage,getattr(args,'topic',None))
    binding = None
    destination = None
    if args.command in {'record', 'capture-mlflow'}:
        Selections(store, 'record-location').require(args.topic)
    config = read_json(args.config) if args.config and args.command in {'capture-mlflow','sync','archive'} else {}
    if args.command == 'template-context':
        if not 1<=args.max_bytes<=5_000_000:raise ValueError('Recommendation reads need a bounded size limit')
        from .common import digest
        files=[];remaining=args.max_bytes
        for file in args.file:
            path=within(file,active['definition']['source_roots'])
            if path.stat().st_size>remaining:raise ValueError('Selected recommendation material exceeds the explicit read limit')
            raw=path.read_bytes();remaining-=len(raw)
            if remaining<0:raise ValueError('Source changed while reading recommendation material')
            files.append({'source':str(path),'sha256':digest(raw),'text':raw.decode('utf-8-sig')})
        output=save_private(store,args.out or store.root/'template-context.json',
                            {'purpose':'template_recommendation_only','intake_version':args.intake,'files':files,
                             'allowed':'Recommend template structure only. No experiment execution, recording, research synthesis or publishing.'})
        return {'status':'needs_agent_template_recommendation','output':output,'files':len(files),
                'template_adopted':False}
    if args.command == 'doctor':
        import shutil
        return {'core': 'available', 'platform_required': False, 'lark_cli': bool(shutil.which('lark-cli.exe') or shutil.which('lark-cli')),
                'network_performed': False, 'private_store': str(store.root)}
    if args.command == 'record':
        authorized=active['definition']['source_roots']
        for root in args.root:within(root,authorized)
        for path in args.file:within(path,authorized)
        paths = [within(p, args.root) for p in args.file]
        parsed = [read_result(p) for p in paths]
        metadata = parsed[0]['data'] if parsed[0]['format'] == 'json' and isinstance(parsed[0]['data'], dict) else {}
        roots = list(args.root)
        if args.metadata:
            meta_path = within(args.metadata, [*roots, store.root])
            meta_source = read_result(meta_path)
            if not isinstance(meta_source['data'], dict):
                raise ValueError('Metadata sidecar must be a JSON object')
            metadata = meta_source['data']
            if meta_path not in paths:
                paths.append(meta_path); parsed.append(meta_source)
            roots.append(store.root)
        metadata = {**metadata, 'status': metadata.get('status', 'unknown')}
        row = store.record(args.topic, args.source_id, metadata, paths, roots,
                           expected_hashes={str(path): parsed[i]['sha256'] for i, path in enumerate(paths)})
        return {'record_id': row['record_id'], 'revision': row['revision'], 'evidence_files': len(row['evidence'])}
    if args.command == 'capture-mlflow':
        if args.run not in active['definition'].get('mlflow_runs',[]):
            raise ValueError('MLflow Run was not selected in this request')
        settings = config.get('mlflow', {})
        source = MLflowSource(settings['url'], settings['allowed_origins'])
        snap = source.snapshot(args.run, args.history_key)
        from .common import digest
        import tempfile
        incoming_parent = store.root/'incoming'; incoming_parent.mkdir(exist_ok=True)
        incoming = Path(tempfile.mkdtemp(prefix='capture-'+digest([settings['url'], args.run])[:12]+'-', dir=incoming_parent))
        write_json(incoming/'snapshot.json', snap); files = [incoming/'snapshot.json']
        artifact_map = []
        for name in args.artifact:
            raw = source.download_artifact(args.run, name)
            target = incoming/('artifact-'+digest(name)); atomic_bytes(target, raw); files.append(target)
            artifact_map.append({'path': name, 'file': target.name, 'sha256': digest(raw)})
        write_json(incoming/'origin.json', {'origin': settings['url'], 'run_id': args.run, 'artifacts': artifact_map}); files.append(incoming/'origin.json')
        row = store.record(args.topic, 'mlflow:'+settings['url']+':'+args.run,
                           {'status': 'unknown', 'tracking_status': snap['tracking_status'], 'business_stage': snap['business_stage'], 'source_kind': 'mlflow'}, files, [incoming])
        return {'record_id': row['record_id'], 'artifact_files': len(artifact_map), 'tracking_status': snap['tracking_status'], 'business_stage': snap['business_stage']}
    if args.command == 'synthesize':
        knowledge = Knowledge(store)
        if args.prepare:
            try: binding = templates.require(args.topic)
            except TemplateRequired: pass
            try: destination = destinations.require(args.topic)
            except DestinationRequired: pass
            path = args.out or store.root/'drafts'/(args.topic+'-input.json')
            output = save_private(store, path, {'topic': args.topic, 'report_template': binding, 'report_destination': destination,
                                               'current': knowledge.head(args.topic), 'records': store.records(args.topic), 'semantic_synthesis': 'current_authorized_agent_only'})
            return {'status': 'needs_agent_synthesis', 'output': output}
        if not args.draft:
            raise ValueError('Provide an Agent-authored draft or request preparation')
        within(args.draft,[store.root,*active['definition']['source_roots']])
        state = knowledge.update(args.topic, read_json(args.draft), args.expected_version)
        output = None
        if state.get('report_template') and 'report_sections' in read_json(args.draft):
            output = save_private(store, args.out or store.root/'previews'/(args.topic+'.md'), render(state), text=True)
        return {'version': state['version'], 'claims': len(state['claims']), 'preview': output}
    if args.command == 'report-preview':
        binding = templates.require(args.topic)
        state = Knowledge(store).head(args.topic)
        if state is None: raise ValueError('No knowledge to render')
        state = {**state, 'report_template':binding}
        if args.sections is not None:
            within(args.sections,[store.root,*active['definition']['source_roots']])
            state['report_sections'] = read_json(args.sections)
        output = save_private(store, args.out or store.root/'previews'/(args.topic+'.md'), render(state), text=True)
        return {'preview':output, 'knowledge_version':state['version'], 'template_version':binding['version']}
    if args.command == 'compare':
        left, right = store.get(args.left), store.get(args.right)
        if any(r['topic']!=active['definition']['topic'] for r in [left,right]):
            raise ValueError('Comparison is outside the confirmed topic')
        result = compare(left, right, args.metric, args.changed_variable)
        output = save_private(store, args.out or store.root/'comparisons'/'latest.json', result)
        return {'comparability': result['comparability'], 'output': output, 'decision_changed': False}
    if args.command == 'organize':
        within(args.input,[*active['definition']['source_roots'],store.root])
        for file in [args.mapping,args.main]:
            if file is not None:within(file,[store.root,*active['definition']['source_roots']])
        parsed = read_result(args.input); value = parsed['data']
        xml = value['data']['document']['content'] if isinstance(value, dict) else value
        if not isinstance(xml, str):
            raise ValueError('Expected a full DocxXML snapshot or fetch envelope')
        result = migration_preview(xml, read_json(args.mapping), args.main.read_text(encoding='utf-8')) if args.mapping and args.main else inventory(xml)
        output = save_private(store, args.out, result)
        return {'output': output, 'apply_authorized': False}
    if args.command == 'verify':
        return store.verify(args.record)
    if args.command == 'reindex':
        return store.reindex()
    if args.command == 'trace':
        if args.record and store.get(args.record)['topic']!=active['definition']['topic']:
            raise ValueError('Trace is outside the confirmed topic')
        data = store.trace(args.record) if args.record else Knowledge(store).trace(args.topic, args.claim)
        return {'output': save_private(store, args.out, data)}
    if args.command == 'sync':
        plan = read_json(args.plan) if args.plan else None
        if args.operation == 'plan':
            if plan is not None:
                raise ValueError('A new plan cannot reuse a loaded plan')
            if not args.topic:
                raise TemplateRequired()
            binding = templates.require(args.topic)
            destination = destinations.require(args.topic)
            adapter, target, roots = destinations.resolve(destination, args.adapter, args.target, args.root)
            if adapter not in active['definition']['reports']:
                raise ValueError('Report output was not requested in this intake')
        elif plan:
            authorize(plan, plan['plan_id']); validate_template_ref(plan)
            ref = plan.get('report_template')
            if args.operation == 'apply':
                if plan.get('intake_version')!=args.intake:
                    raise IntakeRequired('Regenerate the new write plan under this confirmed request')
                if not ref:
                    raise TemplateRequired()
                binding = templates.require(ref['topic'])
                if binding['version'] != ref['version']:
                    raise ValueError('Template changed; regenerate and review the report update plan')
                destination_ref = plan.get('report_destination')
                if destination_ref is None:
                    raise DestinationRequired(ref['topic'])
                destination = destinations.require(destination_ref['topic'])
                if destination['version'] != destination_ref['version']:
                    raise ValueError('Save method or location changed; regenerate and review the report update plan')
                destinations.resolve(destination, plan['adapter'], plan['target'], plan.get('allowed_roots', []))
                if plan.get('report_knowledge'):
                    current = Knowledge(store).head(ref['topic'])
                    if current is None or current['version'] != plan['report_knowledge']['version']:
                        raise ValueError('Knowledge changed; regenerate the reviewed report plan')
            elif ref:
                # Historical bindings remain usable for audit and recovery.
                templates.get(ref['topic'], ref['version'])
            if args.operation != 'apply' and plan.get('report_destination'):
                ref = plan['report_destination']; destinations.get(ref['topic'], ref['version'])
        if plan:
            adapter, target = plan['adapter'], plan['target']
            if active and (not plan.get('report_template') or plan['report_template']['topic']!=active['definition']['topic']):
                raise ValueError('Report operation is outside this confirmed request')
        elif args.operation != 'plan':
            raise ValueError('An existing reviewed plan is required')
        if adapter == 'markdown':
            client = MarkdownSync(store.root/'sync')
        else:
            from .feishu import LarkDocument
            document = target
            allowed = config.get('feishu', {}).get('allowed_documents', [])
            client = FeishuSync(LarkDocument(document, allowed, store.root/'lark', args.allow_feishu_write), store.root/'sync')
        if args.operation == 'plan':
            for file in [args.content,args.replacements]:
                if file is not None:within(file,[store.root,*active['definition']['source_roots']])
            plan = client.plan(target, args.content.read_text(encoding='utf-8'), roots) if adapter == 'markdown' else client.plan(read_json(args.replacements))
            del plan['plan_id']
            plan['report_template'] = {'topic': binding['topic'], 'version': binding['version']}
            plan['report_destination'] = {'topic': destination['topic'], 'version': destination['version']}
            plan['intake_version']=args.intake
            current = Knowledge(store).head(binding['topic'])
            if current:
                plan['report_knowledge'] = {'topic':binding['topic'], 'version':current['version']}
            sealed(plan)
            out = save_private(store, args.out or store.root/'plans'/(plan['plan_id']+'.json'), plan)
            return {'plan_id': plan['plan_id'], 'output': out, 'apply_authorized': False}
        if not plan:
            raise ValueError('An existing reviewed plan is required')
        if args.operation == 'resolve-unknown':
            if adapter != 'feishu':
                raise ValueError('Unknown-outcome resolution applies to Feishu')
            return client.resolve_unknown(plan, args.approve, args.confirm_not_applied)
        return client.verify(plan) if args.operation == 'verify' else getattr(client, args.operation)(plan, args.approve)
    if args.command == 'archive':
        sync = ArchiveSync(store)
        if args.operation == 'plan':
            if not args.topic or args.plan:
                raise ValueError('Select a topic for a new archive plan')
            definition=active['definition']
            if definition['archives']=='none':raise ValueError('No archive output requested')
            budget=args.max_bytes if args.max_bytes is not None else definition['max_archive_bytes']
            if budget>definition['max_archive_bytes']:raise ValueError('Archive limit exceeds this confirmed request')
            plan = sync.plan(args.topic, budget)
            del plan['plan_id'];plan['intake_version']=args.intake;sealed(plan)
            output = save_private(store, args.out or store.root/'archive-plans'/(plan['plan_id']+'.json'), plan)
            return {'plan_id': plan['plan_id'], 'scope': plan['scope'], 'records': plan['records'], 'files': len(plan['inventory']),
                    'bytes': plan['bytes'], 'output': output, 'upload_authorized': False}
        if args.plan is None:
            raise ValueError('A reviewed archive plan is required')
        plan = read_json(args.plan)
        if active and plan['topic']!=active['definition']['topic']:
            raise ValueError('Archive operation is outside the confirmed topic')
        if args.operation in {'apply','adopt'} and plan.get('intake_version')!=args.intake:
            raise IntakeRequired('Regenerate the archive plan under this confirmed request')
        sync._validate(plan, current=args.operation in {'apply', 'adopt'}, bundle=args.operation in {'apply', 'adopt'})
        if args.operation == 'apply':
            authorize(plan, args.approve)
            if not args.allow_feishu_upload:
                raise ValueError('Explicit upload authorization is required')
        if args.operation == 'resolve-unknown':
            return sync.resolve_not_uploaded(plan, args.approve, args.confirm_not_uploaded)
        from .drive import LarkDrive
        kind, target = archive_target(plan)
        settings = config.get('feishu', {})
        if kind == 'wiki':
            client = LarkDrive(settings.get('allowed_archive_wiki_nodes', []), store.root/'lark-drive', args.allow_feishu_upload, target_kind='wiki')
        else:
            client = LarkDrive(settings.get('allowed_archive_folders', []), store.root/'lark-drive', args.allow_feishu_upload)
        sync.client = client
        if args.operation == 'verify':
            result = sync.verify(plan)
        elif args.operation == 'reconcile':
            result = sync.reconcile(plan, args.approve, args.file_token)
        elif args.operation == 'adopt':
            result = sync.adopt(plan, args.approve, args.file_token)
        else:
            result = sync.apply(plan, args.approve)
        return {'verified': result['verified'], 'plan_id': plan['plan_id'], 'receipt': str(sync._state_file(plan))}
    raise ValueError('Unknown operation')

def main(argv=None):
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    args = parser().parse_args(argv)
    try:
        result = run(args)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get('verified', True) else 1
    except TemplateRequired:
        print(json.dumps({'status': 'needs_template_selection', 'message': 'First select an existing template or preview a new one, then explicitly confirm its version. No report workflow was started.'}))
        return 2
    except IntakeRequired as exc:
        print(json.dumps({'status':'needs_request_confirmation',
                          'reason':exc.reason,
                          'message':'First clarify goal, scope and requirements; select a template and exact save locations; confirm this request before accessing experiment payloads.'}))
        return 2
    except DestinationRequired:
        print(json.dumps({'status': 'needs_destination_selection', 'message': 'First select and explicitly confirm the report save method and location. No report workflow was started.'}))
        return 2
    except DestinationTargetRequired:
        print(json.dumps({'status': 'needs_destination_adapter', 'message': 'Both destinations are selected. Create and verify one plan per selected adapter; do not silently omit either output.'}))
        return 2
    except SelectionRequired as exc:
        print(json.dumps({'status':'needs_'+exc.kind.replace('-','_')+'_selection',
                          'message':'Confirm only the missing private location or archive scope for this stage. No payload was printed or uploaded.'}))
        return 2
    except FeishuPermissionError as exc:
        print(json.dumps({'status': 'needs_feishu_authorization', 'missing_scopes': exc.missing_scopes,
                          'message': 'The selected operation needs these scope(s). No automatic login, permission change or upload retry was performed.'}))
        return 2
    except Exception as exc:
        # Do not echo JSON decode snippets, URLs, private file content, or CLI stderr.
        print(json.dumps({'error': type(exc).__name__, 'message': 'Operation stopped; no experiment payload is printed. Check the private inputs and adapter configuration.'}))
        return 1
