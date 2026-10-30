"""Content-addressed evidence and immutable records outside the distribution."""
import json
import sqlite3
import time
from pathlib import Path
from .common import atomic_bytes, canonical, digest, identifier, lock, no_symlinks, read_json, within, write_json, display_path

class Store:
    def __init__(self, root):
        self.root = no_symlinks(root)
        code = no_symlinks(Path(__file__).resolve().parents[2])
        if self.root.is_relative_to(code):
            raise ValueError('Private data must live outside the source/distribution directory')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def record(self, topic, source_key, metadata, files, allowed_roots, expected_hashes=None):
        identifier(topic)
        if not source_key or not files or not allowed_roots:
            raise ValueError('Source identity, evidence and authorized roots required')
        metadata = json.loads(canonical(metadata))
        if metadata.get('status', 'unknown') not in {'completed', 'failed', 'aborted', 'partial', 'unknown'}:
            raise ValueError('Only existing results or partial snapshots may be recorded')
        payloads, evidence = {}, []
        for file in files:
            path = within(file, allowed_roots)
            if not path.is_file():
                raise ValueError('Evidence is not a regular file')
            raw = path.read_bytes(); sha = digest(raw)
            if expected_hashes is not None and expected_hashes.get(str(path)) != sha:
                raise ValueError('Source changed between metadata extraction and archival')
            payloads[sha] = raw
            evidence.append({'origin': display_path(path), 'sha256': sha, 'bytes': len(raw), 'object': f'objects/{sha}'})
        record_id = digest({'topic': topic, 'source_key': source_key})[:24]
        body = {'schema_version': 1, 'record_id': record_id, 'topic': topic, 'source_key': source_key,
                'metadata': metadata, 'evidence': sorted(evidence, key=lambda e: e['origin'])}
        revision = digest(body); body['revision'] = revision
        folder = self.root/'records'/record_id
        with lock(self.root):
            for sha, raw in payloads.items():
                obj = self.root/'objects'/sha
                if obj.exists():
                    if digest(obj.read_bytes()) != sha:
                        raise ValueError('Existing evidence is corrupt')
                else:
                    atomic_bytes(obj, raw)
            revision_path = folder/(revision+'.json')
            if not revision_path.exists():
                write_json(revision_path, body)
            # Immutable revisions are authoritative; manifest is an atomic ordered history.
            manifest = read_json(folder/'history.json') if (folder/'history.json').exists() else []
            if revision not in manifest:
                manifest.append(revision)
            write_json(folder/'history.json', manifest)
            write_json(folder/'head.json', {'revision': revision})
        return body

    def get(self, record_id, revision=None):
        identifier(record_id)
        folder = self.root/'records'/record_id
        revision = revision or read_json(folder/'head.json')['revision']
        identifier(revision)
        value = read_json(no_symlinks(folder/(revision+'.json')))
        check = {k: v for k, v in value.items() if k != 'revision'}
        if digest(check) != revision or value['record_id'] != record_id:
            raise ValueError('Record integrity mismatch')
        return value

    def history(self, record_id):
        identifier(record_id)
        return [self.get(record_id, rev) for rev in read_json(self.root/'records'/record_id/'history.json')]

    def records(self, topic=None):
        if topic is not None:
            identifier(topic)
        rows = [self.get(p.parent.name) for p in (self.root/'records').glob('*/head.json')]
        return sorted([r for r in rows if topic is None or r['topic'] == topic], key=lambda r: r['record_id'])

    def verify(self, record_id):
        row = self.get(record_id)
        results = []
        for e in row['evidence']:
            obj = within(self.root/e['object'], [self.root/'objects'])
            results.append(obj.is_file() and digest(obj.read_bytes()) == e['sha256'])
        return {'record_id': record_id, 'verified': all(results), 'objects': len(results)}

    def trace(self, record_id, revision=None):
        return self.get(record_id, revision)

    def reindex(self):
        with lock(self.root):
            with sqlite3.connect(no_symlinks(self.root/'index.sqlite3')) as db:
                db.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, topic TEXT, revision TEXT)')
                db.execute('DELETE FROM records')
                db.executemany('INSERT INTO records VALUES (?,?,?)', [(r['record_id'], r['topic'], r['revision']) for r in self.records()])
        return {'indexed': len(self.records())}
