"""Explicit local reads and optional, read-only MLflow access."""
import csv
import io
import json
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from .common import canonical, digest, no_symlinks

def read_result(path, mode='structured'):
    """Extract finite structured values or describe inert, byte-exact evidence.

    Auto/raw never import code, deserialize executable objects, or normalize the
    original. Raw-only sources cannot contribute automatically extracted metrics.
    Metadata sidecars must continue to use structured mode.
    """
    if mode not in {'auto','structured','raw'}:
        raise ValueError('Unknown source mode')
    path = no_symlinks(path)
    kind = path.suffix.lower().lstrip('.')
    raw = path.read_bytes()
    descriptor={'format':kind or 'unknown','sha256':digest(raw),'bytes':len(raw),'rows':None,
                'data':None,'extraction':'raw_only','execution_performed':False}
    def inert(reason):
        return {**descriptor,'reason':reason}
    if mode=='raw':return inert('explicit_raw')
    if kind not in {'json','jsonl','csv','txt','log','md','xml'}:
        if mode=='auto':return inert('unparsed_format')
        raise ValueError('Unsupported structured format; source code is never executed')
    try:
        text=raw.decode('utf-8-sig')
    except UnicodeError:
        if mode=='auto':return inert('non_utf8')
        raise ValueError('Structured sources require UTF-8') from None
    try:
        if kind=='json':data=json.loads(text)
        elif kind=='jsonl':data=[json.loads(line) for line in text.splitlines() if line.strip()]
        elif kind=='csv':data=list(csv.DictReader(io.StringIO(text)))
        else:data=text
    except (ValueError,csv.Error):
        if mode=='auto':return inert('invalid_structure')
        raise ValueError('Invalid structured source') from None
    try:
        canonical(data)
    except ValueError:
        if mode=='auto':return inert('nonfinite_number')
        raise ValueError('Structured numbers must be finite') from None
    return {**descriptor,'rows':len(data) if isinstance(data,list) else 1,
            'data':data,'extraction':'structured','reason':None}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Cross-origin redirects are disabled')

class MLflowSource:
    def __init__(self, base_url, allowed_origins, transport=None):
        value = urllib.parse.urlsplit(base_url)
        origin = f'{value.scheme}://{value.netloc}'
        if value.username or value.password or value.query or value.fragment or value.path not in {'', '/'}:
            raise ValueError('Use a credential-free origin URL')
        if origin not in allowed_origins or value.scheme not in {'http', 'https'}:
            raise ValueError('MLflow origin is not authorized')
        if value.scheme == 'http' and value.hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise ValueError('Use HTTPS or a local protected tunnel')
        self.base_url, self.transport = origin, transport
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def _call(self, method, path, body=None):
        endpoint = path.split('?', 1)[0]
        allowed = {'GET': {'runs/get', 'metrics/get-history', 'artifacts/list'},
                   'POST': {'runs/search', 'experiments/search'}}
        if endpoint not in allowed.get(method, set()):
            raise ValueError('Only MLflow read operations are allowed')
        if self.transport:
            return self.transport(method, path, body)
        request = urllib.request.Request(self.base_url+'/api/2.0/mlflow/'+path,
                                         data=canonical(body) if body is not None else None,
                                         method=method, headers={'Content-Type': 'application/json'})
        with self.opener.open(request, timeout=15) as response:
            raw = response.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('Response exceeds configured read bound')
        return json.loads(raw)

    def _pages(self, method, endpoint, body=None, query=None, result_key='runs'):
        results, token, seen = [], None, set()
        for _ in range(100):
            payload = dict(body or {}); params = dict(query or {})
            if token:
                (payload if method == 'POST' else params)['page_token'] = token
            path = endpoint + ('?' + urllib.parse.urlencode(params) if params else '')
            page = self._call(method, path, payload if method == 'POST' else None)
            results.extend(page.get(result_key, []))
            token = page.get('next_page_token')
            if not token:
                return results
            if token in seen:
                raise ValueError('Repeated pagination token')
            seen.add(token)
        raise ValueError('Pagination bound reached; source is incomplete')

    def search_runs(self, experiment_id):
        return {'runs': self._pages('POST', 'runs/search',
                                    {'experiment_ids': [str(experiment_id)], 'max_results': 100})}

    def snapshot(self, run_id, history_keys=()):
        from datetime import datetime, timezone
        observed_at = datetime.now(timezone.utc).isoformat()
        run = self._call('GET', 'runs/get?'+urllib.parse.urlencode({'run_id': run_id}))['run']
        if run['info']['run_id'] != run_id:
            raise ValueError('Unexpected Run identity')
        tags = {r['key']: r['value'] for r in run.get('data', {}).get('tags', [])}
        stage = next((v for k, v in tags.items() if k.endswith('stage_status')), 'unknown')
        history = {key: self._pages('GET', 'metrics/get-history', query={'run_id': run_id, 'metric_key': key}, result_key='metrics') for key in history_keys}
        artifacts = self._pages('GET', 'artifacts/list', query={'run_id': run_id}, result_key='files')
        return {'source_kind': 'mlflow', 'run_id': run_id, 'run': run, 'observed_at': observed_at,
                'tracking_status': run['info']['status'], 'business_stage': stage,
                'parent_run_id': tags.get('mlflow.parentRunId'), 'metric_history': history,
                'artifacts': artifacts, 'artifact_payloads_downloaded': False}

    def download_artifact(self, run_id, relative_path):
        path = PurePosixPath(relative_path)
        if path.is_absolute() or '..' in path.parts or '\\' in relative_path or ':' in relative_path:
            raise ValueError('Unsafe artifact path')
        run = self._call('GET', 'runs/get?'+urllib.parse.urlencode({'run_id': run_id}))['run']
        if run['info']['run_id'] != run_id:
            raise ValueError('Unexpected Run identity')
        uri = run['info']['artifact_uri']
        if not uri.startswith('mlflow-artifacts:/') or urllib.parse.urlsplit(uri).netloc:
            raise ValueError('Only same-origin proxied artifacts are supported')
        prefix = uri.removeprefix('mlflow-artifacts:/').strip('/')
        if '..' in PurePosixPath(prefix).parts:
            raise ValueError('Unsafe artifact store path')
        url = self.base_url+'/api/2.0/mlflow-artifacts/artifacts/'+urllib.parse.quote(prefix+'/'+relative_path, safe='/')
        with self.opener.open(url, timeout=15) as response:
            raw = response.read(64 * 1024 * 1024 + 1)
        if len(raw) > 64 * 1024 * 1024:
            raise ValueError('Artifact exceeds read bound')
        return raw
