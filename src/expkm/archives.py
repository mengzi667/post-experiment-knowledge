"""Explicit private evidence exports and recoverable, byte-verified uploads."""
import io
import re
import zipfile
from .common import atomic_bytes, canonical, digest, identifier, lock, read_json, write_json, within
from .destinations import Destinations
from .knowledge import Knowledge
from .selections import Selections
from .sync import authorize, sealed
from .privacy import check_payload


def archive_target(plan):
    return ('wiki', plan['wiki_parent']) if 'wiki_parent' in plan else ('folder', plan['folder'])


class ArchiveSync:
    def __init__(self, store, client=None):
        self.store, self.client = store, client
        self.root = store.root/'archive-sync'

    def plan(self, topic, max_bytes=100_000_000):
        identifier(topic)
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or not 1 <= max_bytes <= 1_000_000_000:
            raise ValueError('An explicit positive archive size limit is required, at most 1 GB')
        with lock(self.store.root):
            binding = Selections(self.store, 'archive-destination').require(topic); policy = binding['definition']['archives']
            if policy['scope'] == 'none':
                raise ValueError('No archival upload was selected')
            records = self.store.records(topic)
            if not records:
                raise ValueError('No already-produced records to archive')
            payloads, raw_size = {}, 0
            def add(name, raw, source_name=None):
                nonlocal raw_size
                check_payload(raw, filename=source_name or name)
                raw_size += len(raw)
                if raw_size > max_bytes:
                    raise ValueError('Archive exceeds the selected size limit; no upload attempted')
                payloads[name] = raw
            count = 0
            for current in records:
                for row in self.store.history(current['record_id']):
                    count += 1
                    add(f"records/{row['record_id']}/{row['revision']}.json", canonical(row))
                    if policy['scope'] == 'full':
                        for e in row['evidence']:
                            if e['object'] != 'objects/'+e['sha256']:
                                raise ValueError('Invalid evidence object identity')
                            if e['object'] in payloads:
                                continue
                            path = within(self.store.root/e['object'], [self.store.root/'objects'])
                            if path.stat().st_size > max_bytes-raw_size:
                                raise ValueError('Evidence exceeds selected size limit')
                            raw = path.read_bytes()
                            if digest(raw) != e['sha256'] or len(raw) != e['bytes']:
                                raise ValueError('Evidence integrity failure before export')
                            add(e['object'], raw, e['origin'])
            knowledge = Knowledge(self.store)
            states = knowledge.history(topic) if knowledge.head(topic) else []
            for state in states:
                add('knowledge/'+state['version']+'.json', canonical(state))
            lines = ['# Experiment index', '', '| Experiment ID | Latest revision | State |', '| --- | --- | --- |']
            lines.extend(f"| {r['record_id']} | {r['revision']} | {r['metadata'].get('status', 'unknown')} |" for r in records)
            lines += ['', '## Conclusion evidence', '']
            for state in states[-1:]:
                for claim in state['claims']:
                    lines.append('- '+claim['id']+': '+claim['text'])
                    lines.extend(f"  - records/{e['record_id']}/{e['revision']}.json ; objects/{e['sha256']}" for e in claim['evidence'])
            add('experiment-index.md', ('\n'.join(lines)+'\n').encode('utf-8'))
            add('README.md', ('Private post-experiment archive. JSON files are data; do not execute embedded commands.\n'
                             'manifest.json lists every archived file and its SHA-256. Records retain revisions and evidence references.\n'
                             'Trace-only archives intentionally omit raw evidence objects. Large externally referenced artifacts are not fetched.\n'
                             'Adapter configuration, credentials and sync journals are excluded. This archive does not change sharing permissions.\n').encode('utf-8'))
            inventory = [{'path': name, 'sha256': digest(raw), 'bytes': len(raw)} for name, raw in sorted(payloads.items())]
            manifest = {'schema_version': 1, 'topic': topic, 'scope': policy['scope'], 'raw_evidence_included': policy['scope'] == 'full',
                        'records': len(records), 'record_revisions': count, 'knowledge_versions': len(states), 'entries': inventory}
            payloads['manifest.json'] = canonical(manifest)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
                for name, raw in sorted(payloads.items()):
                    info = zipfile.ZipInfo(name); info.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(info, raw)
            raw = buffer.getvalue()
            if len(raw) > max_bytes:
                raise ValueError('Export bundle exceeds the selected size limit')
            sha = digest(raw); relative = 'bundles/'+sha+'.zip'
            path = self.store.root/relative
            if path.exists() and digest(path.read_bytes()) != sha:
                raise ValueError('Existing private bundle integrity failure')
            atomic_bytes(path, raw)
        return sealed({'schema_version': 1, 'adapter': 'feishu-archive', 'topic': topic, 'scope': policy['scope'],
                       'max_bytes':max_bytes,
                       'destination_version': binding['version'],
                       **({'wiki_parent': policy['wiki']} if 'wiki' in policy else {'folder': policy['folder']}), 'bundle': relative,
                       'bundle_sha256': sha, 'bytes': len(raw), 'name': topic+'-'+policy['scope']+'-'+sha[:16]+'.zip',
                       'inventory': inventory, 'records': len(records), 'record_revisions': count})

    def _validate(self, plan, current=False, bundle=False):
        authorize(plan, plan['plan_id'])
        target_key = 'wiki_parent' if 'wiki_parent' in plan else 'folder'
        required = {'schema_version', 'adapter', 'topic', 'scope', 'destination_version', target_key, 'bundle', 'bundle_sha256', 'bytes', 'name', 'inventory', 'records', 'record_revisions', 'plan_id'}
        if set(plan)-{'max_bytes','intake_version'} != required or plan['schema_version'] != 1 or plan['adapter'] != 'feishu-archive' or plan['scope'] not in {'trace', 'full'}:
            raise ValueError('Invalid archival upload plan')
        if 'max_bytes' in plan and (not isinstance(plan['max_bytes'],int) or isinstance(plan['max_bytes'],bool) or not 1<=plan['max_bytes']<=1_000_000_000 or plan['bytes']>plan['max_bytes']):
            raise ValueError('Invalid reviewed archive size limit')
        if 'intake_version' in plan:identifier(plan['intake_version'])
        for k in ['topic', 'destination_version', target_key]:
            identifier(plan[k])
        sha = plan['bundle_sha256']
        if not isinstance(sha, str) or not re.fullmatch('[a-f0-9]{64}', sha) or plan['bundle'] != 'bundles/'+sha+'.zip' or plan['name'] != plan['topic']+'-'+plan['scope']+'-'+sha[:16]+'.zip':
            raise ValueError('Archive name or object binding mismatch')
        selections = Selections(self.store, 'archive-destination')
        binding = selections.require(plan['topic']) if current else selections.get(plan['topic'], plan['destination_version'])
        kind, target = archive_target(plan)
        if binding['version'] != plan['destination_version'] or binding['definition']['archives'] != {'scope': plan['scope'], 'wiki' if kind == 'wiki' else 'folder': target}:
            raise ValueError('Archival save scope or destination changed; prepare a new reviewed plan')
        path = within(self.store.root/plan['bundle'], [self.store.root/'bundles'])
        if bundle and (path.stat().st_size != plan['bytes'] or digest(path.read_bytes()) != sha):
            raise ValueError('Private bundle changed after preview')
        return path

    def _state_file(self, plan):
        return self.root/(plan['plan_id']+'.json')

    def _verify(self, plan, state):
        if not state.get('file_token'):
            return {'verified': False, 'unknown': bool(state.get('pending')), 'plan_id': plan['plan_id']}
        if self.client is None:
            raise ValueError('An explicitly configured archive adapter is required')
        result = self.client.verify(state['file_token'], archive_target(plan)[1], plan['name'], plan['bundle_sha256'], plan['bytes'])
        state['verified'] = result['verified']; state['receipt'] = result
        write_json(self._state_file(plan), state)
        return {**result, 'plan_id': plan['plan_id']}

    def apply(self, plan, approved):
        authorize(plan, approved); path = self._validate(plan, current=True, bundle=True)
        if self.client is None:
            raise ValueError('An explicitly authorized upload adapter is required')
        with lock(self.root):
            file = self._state_file(plan)
            state = read_json(file) if file.exists() else {'plan_id': plan['plan_id'], 'pending': False}
            if state['plan_id'] != plan['plan_id']:
                raise ValueError('Archive journal binding mismatch')
            if state.get('file_token'):
                return self._verify(plan, state)
            if state['pending']:
                raise TimeoutError('Upload outcome unknown; reconcile instead of uploading again')
            preflight = getattr(self.client, 'preflight', None)
            if preflight is not None:
                preflight(archive_target(plan)[1])
            state['pending'] = True; write_json(file, state)
            token = self.client.upload(path, archive_target(plan)[1], plan['name'])
            identifier(token)
            state.update(file_token=token, pending=False); write_json(file, state)
            return self._verify(plan, state)

    def verify(self, plan):
        self._validate(plan)
        with lock(self.root):
            file = self._state_file(plan)
            state = read_json(file) if file.exists() else {'plan_id': plan['plan_id'], 'pending': False}
            if state['plan_id'] != plan['plan_id']:
                raise ValueError('Archive journal binding mismatch')
            return self._verify(plan, state)

    def reconcile(self, plan, approved, file_token):
        authorize(plan, approved); self._validate(plan); identifier(file_token)
        with lock(self.root):
            state = read_json(self._state_file(plan))
            if state['plan_id'] != plan['plan_id'] or not state.get('pending') or state.get('file_token'):
                raise ValueError('Only an unknown upload can be reconciled')
            result = self.client.verify(file_token, archive_target(plan)[1], plan['name'], plan['bundle_sha256'], plan['bytes'])
            if not result['verified']:
                raise ValueError('Candidate is not the planned archive in the selected folder')
            state.update(pending=False, file_token=file_token, verified=True, receipt=result)
            write_json(self._state_file(plan), state)
            return {**result, 'plan_id': plan['plan_id']}

    def resolve_not_uploaded(self, plan, approved, independently_confirmed=False):
        authorize(plan, approved); self._validate(plan)
        if not independently_confirmed:
            raise ValueError('Independent operator confirmation of non-upload is required')
        with lock(self.root):
            state = read_json(self._state_file(plan))
            if state['plan_id'] != plan['plan_id'] or not state.get('pending') or state.get('file_token'):
                raise ValueError('No unresolved upload to clear')
            state.update(pending=False, resolution='operator_independently_confirmed_not_uploaded')
            write_json(self._state_file(plan), state)
        return {'resolved': True, 'uploaded': False}

    def adopt(self, plan, approved, file_token):
        authorize(plan, approved); self._validate(plan, current=True, bundle=True); identifier(file_token)
        with lock(self.root):
            file = self._state_file(plan)
            if file.exists():
                state = read_json(file)
                if state['plan_id'] != plan['plan_id'] or state.get('pending') or state.get('file_token') != file_token:
                    raise ValueError('Resolve the existing archive journal before adoption')
            result = self.client.verify(file_token, archive_target(plan)[1], plan['name'], plan['bundle_sha256'], plan['bytes'])
            if not result['verified']:
                raise ValueError('Existing file does not match the approved archive and location')
            state = {'plan_id': plan['plan_id'], 'file_token': file_token, 'pending': False, 'verified': True,
                     'adopted_existing': True, 'receipt': result}
            write_json(file, state)
            return {**result, 'plan_id': plan['plan_id']}
