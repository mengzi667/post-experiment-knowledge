"""Allowlisted local distribution only; never publishes or copies runtime data."""
import io
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from .common import atomic_bytes, digest, no_symlinks

MODULES = ('__init__', '__main__', 'common', 'documents', 'store', 'sources', 'templates', 'destinations', 'selections', 'intake', 'cards', 'workflow', 'onboarding', 'archives', 'privacy', 'drive', 'knowledge', 'sync', 'feishu', 'cli', 'packaging', 'installer')
SKILL_FILES = ('SKILL.md', 'agents/openai.yaml', 'scripts/expkm.py', 'scripts/expkm.cmd', 'references/contracts.md', 'references/sync-and-privacy.md', 'references/templates.md', 'references/destinations.md', 'references/archives.md', 'references/intake.md')
RUNTIME_LOCK = 'runtime/windows-x86_64.json'
SPECIALISTS = ('experiment-record','experiment-synthesize','experiment-sync')
PUBLIC_FILES = ('pyproject.toml', 'plugin.json', '.codex-plugin/plugin.json', '.agents/plugins/marketplace.json', 'README.md', 'BETA.md', 'LICENSE', 'install.cmd', 'scripts/install.py', 'ARCHITECTURE.md', 'RESEARCH.md', 'ROADMAP.md', 'VALIDATION.md', 'examples/synthetic30.py', RUNTIME_LOCK) + tuple('src/expkm/'+m+'.py' for m in MODULES) + tuple('skills/post-experiment-knowledge/'+f for f in SKILL_FILES) + tuple('skills/'+s+'/'+f for s in SPECIALISTS for f in ('SKILL.md','agents/openai.yaml'))

def scan(raw):
    text = raw.decode('utf-8')
    if re.search(r'AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
        raise ValueError('Potential secret in distribution')
    if re.search(r'[A-Za-z]:[\\/]Users[\\/][^\s"\']+', text):
        raise ValueError('User-specific absolute path in distribution')
    allowed = {'127.0.0.1', 'localhost', 'developers.openai.com', 'learn.chatgpt.com', 'agent-plugins.org', 'mlflow.org', 'www.python.org', 'docs.python.org'}
    from urllib.parse import urlsplit
    for url in re.findall(r'https?://[a-zA-Z0-9@._:/-]+', text):
        host = urlsplit(url).hostname
        if host and host not in allowed and not host.endswith('.invalid'):
            raise ValueError('Unreviewed network location in distribution')

def payloads(source):
    source = no_symlinks(source)
    values = {}
    for relative in PUBLIC_FILES:
        path = no_symlinks(source/relative)
        if not path.is_relative_to(source) or not path.is_file():
            raise ValueError('Distribution source is incomplete')
        raw = path.read_bytes(); scan(raw); values[relative] = raw
    return values

def runtime_payloads(source, archive):
    """Only the exact official ZIP pinned in the public lock can supply binaries."""
    source, archive = no_symlinks(source), no_symlinks(archive)
    descriptor = json.loads((source/RUNTIME_LOCK).read_text(encoding='utf-8'))
    if (descriptor.get('schema_version') != 1 or descriptor.get('platform') != 'windows-x86_64'
            or descriptor.get('implementation') != 'CPython'):
        raise ValueError('Unsupported bundled runtime descriptor')
    raw = archive.read_bytes()
    if digest(raw) != descriptor['archive_sha256']:
        raise ValueError('Bundled runtime archive checksum mismatch')
    entries = {e['path']: e for e in descriptor['files']}
    if (len(entries) != len(descriptor['files']) or not {'python.exe', 'LICENSE.txt'}.issubset(entries)
            or not any(n.endswith('._pth') for n in entries)
            or any(not re.fullmatch(r'[A-Za-z0-9_.-]+', name) for name in entries)):
        raise ValueError('Invalid bundled runtime file allowlist')
    values = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
        if len(zipped.namelist()) != len(entries) or set(zipped.namelist()) != set(entries):
            raise ValueError('Unexpected bundled runtime entries')
        for name, entry in entries.items():
            value = zipped.read(name)
            if len(value) != entry['bytes'] or digest(value) != entry['sha256']:
                raise ValueError('Bundled runtime file checksum mismatch')
            values[name] = value
    return descriptor, values


def build_plugin(source, destination, windows_runtime=None):
    source, destination = no_symlinks(source), no_symlinks(destination)
    if destination.is_relative_to(source):
        raise ValueError('Build output must be outside the source tree')
    files = payloads(source); binary_files = {}; runtime_version = None
    if windows_runtime is not None:
        descriptor, binaries = runtime_payloads(source, windows_runtime)
        runtime_version = descriptor['version']
        binary_files = {'skills/post-experiment-knowledge/python/'+n: raw for n, raw in binaries.items()}
        files.update(binary_files)
    manifest = {'schema_version': 1, 'name': 'post-experiment-knowledge',
                'version': json.loads(files['plugin.json'])['version'], 'bundled_python': runtime_version,
                'entries': [{'path': name, 'bytes': len(raw), 'sha256': digest(raw)} for name, raw in sorted(files.items())]}
    files['release-manifest.json'] = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        for relative, raw in files.items():
            archive.writestr('post-experiment-knowledge/'+relative, raw)
    raw = buf.getvalue()
    # Check the actual artifact, not only the staging inputs.
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if (len(archive.namelist()) != len(files)
                or set(archive.namelist()) != {'post-experiment-knowledge/'+n for n in files}):
            raise ValueError('Unexpected release entries')
        for name in archive.namelist():
            relative = name.removeprefix('post-experiment-knowledge/')
            value = archive.read(name)
            if relative in binary_files:
                if value != binary_files[relative]:
                    raise ValueError('Bundled runtime changed in final artifact')
            else:
                scan(value)
    atomic_bytes(destination, raw)
    return {'verified': True, 'files': len(files), 'sha256': digest(raw), 'published': False,
            'bundled_python': runtime_version, 'platform': 'windows-x86_64' if runtime_version else 'source-only'}

def install_skill(source, destination, windows_runtime=None):
    """Legacy single-entry installation. Full four-skill discovery uses the plugin."""
    destination = no_symlinks(destination)
    if destination.exists():
        raise ValueError('Existing skill is never overwritten')
    files = payloads(source); binaries = {}; runtime_version = None
    if windows_runtime is not None:
        descriptor, binaries = runtime_payloads(source, windows_runtime)
        runtime_version = descriptor['version']
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=destination.parent, prefix='.expkm-install-'))
    try:
        for relative in SKILL_FILES:
            atomic_bytes(staging/relative, files['skills/post-experiment-knowledge/'+relative])
        # Companion instructions remain usable through the coordinator even in
        # this legacy non-discoverable layout. One runtime, no sibling overwrite.
        for name in SPECIALISTS:
            for relative in ('SKILL.md', 'agents/openai.yaml'):
                raw = files['skills/'+name+'/'+relative]
                if relative == 'SKILL.md':
                    raw = raw.replace(b'../post-experiment-knowledge/', b'../../')
                atomic_bytes(staging/'companions'/name/relative, raw)
        for module in MODULES:
            atomic_bytes(staging/'runtime'/'expkm'/(module+'.py'), files['src/expkm/'+module+'.py'])
        atomic_bytes(staging/'runtime-lock.json', files[RUNTIME_LOCK])
        for name, raw in binaries.items():
            atomic_bytes(staging/'python'/name, raw)
        staging.rename(destination)
    except Exception:
        # Delete only the known staging directory we just allocated.
        shutil.rmtree(staging)
        raise
    return {'installed': True, 'runtime_bundled': True, 'bundled_python': runtime_version,
            'files': len(SKILL_FILES)+2*len(SPECIALISTS)+len(MODULES)+1+len(binaries)}
