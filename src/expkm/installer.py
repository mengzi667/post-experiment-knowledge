"""Offline user-scoped installation of a verified release; no account changes."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from .common import digest, no_symlinks, write_json, lock


def verified_files(source):
    source = no_symlinks(source)
    raw_manifest = (source/'release-manifest.json').read_bytes()
    manifest = json.loads(raw_manifest)
    if manifest.get('schema_version') != 1 or manifest.get('name') != 'post-experiment-knowledge':
        raise ValueError('Unsupported release manifest')
    files = {}
    for entry in manifest['entries']:
        rel = PurePosixPath(entry['path'])
        if (not rel.parts or rel.is_absolute() or '..' in rel.parts or '\\' in entry['path']
                or ':' in entry['path'] or entry['path'] in files or entry['path'] == 'release-manifest.json'):
            raise ValueError('Unsafe release file entry')
        path = no_symlinks(source/Path(*rel.parts))
        if not path.is_relative_to(source):
            raise ValueError('Release file escapes its package')
        raw = path.read_bytes()
        if len(raw) != entry['bytes'] or digest(raw) != entry['sha256']:
            raise ValueError('Release file checksum mismatch')
        files[entry['path']] = raw
    if not {'plugin.json', '.agents/plugins/marketplace.json', 'install.cmd'}.issubset(files):
        raise ValueError('Incomplete installable release')
    if json.loads(files['plugin.json'])['version'] != manifest['version']:
        raise ValueError('Release version mismatch')
    files['release-manifest.json'] = raw_manifest
    return manifest, files


def find_codex():
    executable = shutil.which('codex.exe') or shutil.which('codex')
    if executable:
        return executable
    if os.name == 'nt' and os.environ.get('LOCALAPPDATA'):
        base = Path(os.environ['LOCALAPPDATA'])/'OpenAI/Codex/bin'
        candidates = sorted(base.glob('*/codex.exe'), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            return str(candidates[0])
    raise ValueError('Codex plugin CLI was not found. Install/update Codex, then run this installer again.')


def install_release(source, destination, codex=None, runner=None):
    manifest, files = verified_files(source)
    destination = no_symlinks(destination)
    if destination == no_symlinks(source):
        raise ValueError('Installation target must be separate from the downloaded package')
    executable = codex or find_codex()
    runner = runner or subprocess.run
    reused = destination.exists()
    if reused:
        _, installed = verified_files(destination)
        if installed != files:
            raise ValueError('Existing installation checksum differs; preserve it and use a new release version')
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = no_symlinks(Path(tempfile.mkdtemp(prefix='.expkm-install-', dir=destination.parent)))
        try:
            for name, raw in files.items():
                path = stage/Path(*PurePosixPath(name).parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            verified_files(stage)
            stage.rename(destination)
        except Exception:
            # Only the freshly allocated staging directory inside this exact parent.
            if stage.exists() and stage.is_relative_to(destination.parent) and stage.name.startswith('.expkm-install-'):
                shutil.rmtree(stage)
            raise
    # One stable user-owned marketplace root; versioned packages remain immutable.
    marketplace = destination.parent
    catalog_file = marketplace/'.agents/plugins/marketplace.json'
    owner_file = marketplace/'.expkm-marketplace-owner.json'
    catalog = json.loads(files['.agents/plugins/marketplace.json'])
    catalog['plugins'][0]['source'] = {'source': 'local', 'path': './'+destination.name}
    with lock(marketplace):
        if catalog_file.exists():
            if not owner_file.exists():
                raise ValueError('Existing marketplace is not owned by this installer; preserve it and choose another target')
            owner = json.loads(owner_file.read_text(encoding='utf-8'))
            if (owner.get('name') != 'post-experiment-knowledge'
                    or owner.get('catalog_sha256') != digest(catalog_file.read_bytes())):
                raise ValueError('Existing marketplace checksum differs; preserve user modifications')
        write_json(catalog_file, catalog)
        write_json(owner_file, {'name': 'post-experiment-knowledge', 'catalog_sha256': digest(catalog_file.read_bytes())})
    for args in ([executable, 'plugin', 'marketplace', 'add', str(marketplace), '--json'],
                 [executable, 'plugin', 'add', 'post-experiment-knowledge@'+catalog['name'], '--json']):
        result = runner(args, capture_output=True, encoding='utf-8', timeout=60)
        if result.returncode:
            raise ValueError('Codex did not confirm plugin installation. Existing files are retained; check Codex plugin support and retry the installer.')
    receipt = {'installed': True, 'reused_existing': reused, 'version': manifest['version'],
               'bundled_python': manifest.get('bundled_python'), 'destination': str(destination),
               'sharing_changed': False, 'credentials_requested': False}
    write_json(destination/'install-receipt.json', receipt)
    return receipt


def main(source):
    parser = argparse.ArgumentParser(description='Install this local Codex plugin without system Python or admin access.')
    parser.add_argument('--no-pause', action='store_true', help='Used by the Windows launcher')
    parser.add_argument('--target', type=Path, help='Optional user-scoped installation directory')
    args = parser.parse_args()
    try:
        manifest, _ = verified_files(source)
        base = Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))/'PostExperimentKnowledge/plugin-marketplace'
        target = args.target or base/manifest['version']
        result = install_release(source, target)
        print('Installed Post-Experiment Knowledge '+result['version']+'.')
        print('Start a new Codex chat and use $post-experiment-knowledge.')
        print('Windows Python is bundled. Feishu requires your own lark-cli and authorization.')
        return 0
    except (ValueError, OSError, subprocess.SubprocessError):
        print('Installation was not completed. Check package integrity and Codex plugin CLI support. Existing data and account permissions were not changed.', file=sys.stderr)
        return 2
