"""Optional lark-cli adapter. No login, sharing or production discovery."""
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from .common import read_json, write_json
from .documents import parse_xml
from .store import Store

class LarkDocument:
    def __init__(self, document, allowed_documents, workspace, write_enabled=False):
        if not document or document not in allowed_documents:
            raise ValueError('Document not explicitly authorized')
        self.document = document
        self.workspace = Store(workspace).root
        self.write_enabled = write_enabled
        self.reference_map = {}
        self.executable = shutil.which('lark-cli.exe') or shutil.which('lark-cli')
        if not self.executable:
            raise ValueError('Optional lark-cli executable is unavailable')

    def _call(self, args, content=None):
        env = {**os.environ, 'LARKSUITE_CLI_NO_UPDATE_NOTIFIER': '1', 'LARKSUITE_CLI_NO_SKILLS_NOTIFIER': '1'}
        try:
            r = subprocess.run([self.executable, 'docs', *args, '--as', 'user'], cwd=self.workspace,
                               input=content.encode('utf-8') if content is not None else None,
                               capture_output=True, timeout=90, env=env)
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError('Feishu operation outcome must be reconciled before retry') from None
        if r.returncode:
            raise ValueError('Feishu CLI did not confirm success; private source output is suppressed')
        import json
        obj = json.loads(r.stdout)
        if not obj.get('ok') or obj.get('data', {}).get('result', 'success') != 'success' or obj.get('data', {}).get('warnings'):
            raise ValueError('Feishu operation incomplete; read back before proceeding')
        return obj['data']

    def read(self):
        d = self._call(['+fetch', '--doc', self.document, '--detail', 'full'])['document']
        self.reference_map = d.get('reference_map', {})
        return {'revision': d['revision_id'], 'blocks': [ET.tostring(n, encoding='unicode') for n in parse_xml(d['content'])]}

    def replace(self, block_id, xml, revision):
        if not self.write_enabled:
            raise ValueError('Feishu client is read-only; explicit write authorization is required')
        args = ['+update', '--doc', self.document, '--command', 'block_replace', '--block-id', block_id,
                '--revision-id', str(revision), '--content', '-']
        if self.reference_map:
            write_json(self.workspace/'reference-map.json', self.reference_map)
            args += ['--reference-map', '@reference-map.json']
        return self._call(args, xml)
