"""Optional private Drive archive transfer, using the existing lark-cli identity."""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from .common import digest, identifier, no_symlinks
from .store import Store


class FeishuPermissionError(ValueError):
    def __init__(self, scopes):
        self.missing_scopes = scopes
        super().__init__('The selected Feishu operation requires additional explicitly granted scope(s)')


class LarkDrive:
    def __init__(self, allowed_folders, workspace, write_enabled=False, runner=None, target_kind='folder'):
        if target_kind not in {'folder', 'wiki'}:
            raise ValueError('Unknown archival target type')
        self.allowed = set(allowed_folders)
        self.target_kind = target_kind
        self.root = Store(workspace).root
        self.write_enabled = write_enabled
        self.runner = runner or subprocess.run
        self.executable = shutil.which('lark-cli.exe') or shutil.which('lark-cli') or ('lark-cli' if runner else None)
        if not self.executable:
            raise ValueError('Optional lark-cli executable is unavailable')

    def _folder(self, folder):
        identifier(folder)
        if folder not in self.allowed:
            raise ValueError('Archive folder is not explicitly allowlisted')

    def _call(self, args, cwd, service='drive'):
        env = {**os.environ, 'LARKSUITE_CLI_NO_UPDATE_NOTIFIER': '1', 'LARKSUITE_CLI_NO_SKILLS_NOTIFIER': '1'}
        try:
            r = self.runner([self.executable, service, *args, '--as', 'user', '--format', 'json'],
                            cwd=cwd, capture_output=True, timeout=55, env=env)
        except subprocess.TimeoutExpired:
            raise TimeoutError('Drive outcome unknown; reconcile before retrying a write') from None
        if r.returncode:
            try:
                error = json.loads(r.stderr).get('error', {})
            except (ValueError, TypeError):
                error = {}
            if not isinstance(error, dict):
                error = {}
            scopes = error.get('missing_scopes', [])
            if error.get('subtype') == 'missing_scope' and isinstance(scopes, list) and scopes and all(isinstance(s, str) and re.fullmatch(r'[a-z][a-z0-9_]*:[a-z0-9_:.-]{1,120}', s) for s in scopes):
                raise FeishuPermissionError(scopes)
            raise ValueError('Drive operation was not confirmed; no automatic retry or permission change')
        try:
            value = json.loads(r.stdout)
        except (ValueError, TypeError):
            raise ValueError('Drive returned an unreadable result; reconcile before retrying a write') from None
        if value.get('ok') is not True or value.get('identity') != 'user' or not isinstance(value.get('data'), dict) or value['data'].get('warnings'):
            raise ValueError('Drive did not confirm the requested user operation')
        return value['data']

    def preflight(self, folder):
        """Check the actual directory-read capability before any upload is issued."""
        self._folder(folder)
        if self.target_kind == 'wiki':
            meta = self._call(['+node-get', '--node-token', folder], self.root, service='wiki')
            if meta.get('node_token') != folder:
                raise ValueError('Wiki parent identity mismatch')
            return
        self._call(['files', 'list', '--params', json.dumps({'folder_token': folder, 'page_size': 1})], self.root)

    def upload(self,path,folder,name):
        self._folder(folder)
        if not self.write_enabled:
            raise ValueError('Explicit upload authorization is required')
        if not isinstance(name, str) or Path(name).name != name or not name.endswith('.zip'):
            raise ValueError('A bound archive filename is required')
        path = no_symlinks(path)
        if not re.fullmatch('[a-f0-9]{64}\\.zip', path.name):
            raise ValueError('Only a content-addressed private bundle may be uploaded')
        with tempfile.TemporaryDirectory(prefix='upload-', dir=self.root) as temporary:
            staged = Path(temporary)/'bundle.zip'; shutil.copyfile(path, staged)
            if digest(staged.read_bytes()) != path.stem:
                raise ValueError('Archive changed before upload')
            flag = '--wiki-token' if self.target_kind == 'wiki' else '--folder-token'
            data = self._call(['+upload', '--file', 'bundle.zip', flag, folder, '--name', name], temporary)
        token = data.get('file_token')
        identifier(token)
        return token

    def verify(self,token,folder,name,sha,size):
        self._folder(folder); identifier(token)
        if self.target_kind == 'wiki':
            meta = self._call(['+node-get', '--node-token', token, '--obj-type', 'file'], self.root, service='wiki')
            matched = (meta.get('obj_token') == token and meta.get('obj_type') == 'file'
                       and meta.get('parent_node_token') == folder and meta.get('title') == name)
            if not matched:
                return {'verified': False, 'file_token': token, 'parent_confirmed': False}
            return self._download_verify(token, sha, size, {'parent_confirmed': True, 'wiki_node_token': meta['node_token'], 'location_type': 'wiki'})
        page = None; seen = set(); match = None
        for _ in range(1000):
            params = {'folder_token': folder, 'page_size': 200}
            if page:
                params['page_token'] = page
            data = self._call(['files', 'list', '--params', json.dumps(params)], self.root)
            if not isinstance(data.get('files'), list) or not isinstance(data.get('has_more'), bool):
                raise ValueError('Folder membership response incomplete')
            for entry in data['files']:
                if entry.get('token') == token:
                    match = entry; break
            if match is not None or not data['has_more']:
                break
            page = data.get('next_page_token')
            if not page or page in seen:
                raise ValueError('Folder verification pagination incomplete')
            seen.add(page)
        else:
            raise ValueError('Folder verification incomplete; no upload retry authorized')
        if not match or match.get('type') != 'file' or match.get('name') != name or match.get('parent_token', folder) != folder:
            return {'verified': False, 'file_token': token, 'folder_confirmed': False}
        return self._download_verify(token, sha, size, {'folder_confirmed': True, **({'url': match['url']} if isinstance(match.get('url'), str) else {})})

    def _download_verify(self, token, sha, size, metadata):
        with tempfile.TemporaryDirectory(prefix='verify-', dir=self.root) as temporary:
            self._call(['+download', '--file-token', token, '--output', 'bundle.zip'], temporary)
            path = no_symlinks(Path(temporary)/'bundle.zip')
            if not path.is_file():
                return {'verified': False, 'file_token': token, **metadata}
            length = path.stat().st_size
            if length != size:
                return {'verified': False, 'file_token': token, **metadata, 'bytes': length}
            actual = digest(path.read_bytes())
        return {'verified': actual == sha, 'file_token': token, **metadata, 'sha256': actual, 'bytes': length}
