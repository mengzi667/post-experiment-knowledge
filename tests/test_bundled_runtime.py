import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

import pytest
import expkm.packaging as packaging


def fixture_runtime(tmp_path):
    source = tmp_path/'source'
    shutil.copytree(Path(__file__).parents[1], source,
                    ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', '.venv', '*.egg-info'))
    contents = {'python.exe': b'SYNTHETIC_EXECUTABLE', 'python314.zip': b'SYNTHETIC_STDLIB',
                'python314._pth': b'python314.zip\n.\n', 'LICENSE.txt': b'SYNTHETIC_LICENSE'}
    runtime = tmp_path/'runtime.zip'
    with zipfile.ZipFile(runtime, 'w') as z:
        for name, raw in contents.items():
            z.writestr(name, raw)
    descriptor = {'schema_version': 1, 'implementation': 'CPython', 'version': '3.14.10',
                  'platform': 'windows-x86_64', 'archive_url': 'https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip',
                  'archive_sha256': hashlib.sha256(runtime.read_bytes()).hexdigest(),
                  'files': [{'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                            for name, raw in sorted(contents.items())]}
    lock = source/'runtime/windows-x86_64.json'
    lock.parent.mkdir(exist_ok=True)
    lock.write_text(json.dumps(descriptor), encoding='utf-8')
    return source, runtime, contents


def test_windows_release_contains_exact_locked_runtime_and_license(tmp_path):
    source, runtime, contents = fixture_runtime(tmp_path)
    assert hasattr(packaging, 'runtime_payloads'), 'Runtime verification is missing'
    result = packaging.build_plugin(source, tmp_path/'release.zip', windows_runtime=runtime)
    assert result['bundled_python'] == '3.14.10'
    with zipfile.ZipFile(tmp_path/'release.zip') as z:
        prefix = 'post-experiment-knowledge/skills/post-experiment-knowledge/python/'
        assert {n[len(prefix):] for n in z.namelist() if n.startswith(prefix)} == set(contents)
        assert all(z.read(prefix+name) == raw for name, raw in contents.items())
        assert any(n.endswith('/scripts/expkm.cmd') for n in z.namelist())


def test_runtime_tampering_fails_before_build_output(tmp_path):
    source, runtime, _ = fixture_runtime(tmp_path)
    assert hasattr(packaging, 'runtime_payloads'), 'Runtime verification is missing'
    runtime.write_bytes(runtime.read_bytes()+b'UNREVIEWED_PAYLOAD')
    output = tmp_path/'release.zip'
    with pytest.raises(ValueError, match='checksum'):
        packaging.build_plugin(source, output, windows_runtime=runtime)
    assert not output.exists()


def test_skill_install_carries_runtime_without_overwriting_existing_skill(tmp_path):
    source, runtime, contents = fixture_runtime(tmp_path)
    assert hasattr(packaging, 'runtime_payloads'), 'Runtime verification is missing'
    dest = tmp_path/'installed-skill'
    result = packaging.install_skill(source, dest, windows_runtime=runtime)
    assert result['bundled_python'] == '3.14.10'
    assert (dest/'python/LICENSE.txt').read_bytes() == contents['LICENSE.txt']
    assert (dest/'scripts/expkm.cmd').exists()
    with pytest.raises(ValueError):
        packaging.install_skill(source, dest, windows_runtime=runtime)


@pytest.mark.skipif(os.name != 'nt' or not os.environ.get('EXPKM_TEST_WINDOWS_RUNTIME'),
                    reason='Live Windows test needs the pinned official runtime ZIP')
def test_clean_windows_plugin_and_skill_work_without_system_python(tmp_path):
    source = Path(__file__).parents[1]
    runtime = Path(os.environ['EXPKM_TEST_WINDOWS_RUNTIME'])
    output = tmp_path/'release.zip'
    packaging.build_plugin(source, output, windows_runtime=runtime)
    extracted = tmp_path/'无系统Python 空格目录'
    with zipfile.ZipFile(output) as z:
        z.extractall(extracted)
    plugin = extracted/'post-experiment-knowledge'
    skill = tmp_path/'独立技能 空格目录'
    packaging.install_skill(source, skill, windows_runtime=runtime)
    env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
    env['PATH'] = str(Path(os.environ['SystemRoot'])/'System32')
    env['PYTHONHOME'] = str(tmp_path/'nonexistent-poison-home')
    env['PYTHONPATH'] = str(tmp_path/'nonexistent-poison-path')
    for target in [plugin/'skills/post-experiment-knowledge', skill]:
        launcher = target/'scripts/expkm.cmd'
        command = f'""{launcher}" --store "{tmp_path / ("private-"+target.parent.name)}" setup --topic synthetic"'
        result = subprocess.run(f'"{os.environ["ComSpec"]}" /d /s /c {command}',
                                cwd=tmp_path, env=env, capture_output=True, encoding='utf-8')
        assert result.returncode == 0, result.stdout+result.stderr
        assert json.loads(result.stdout)['status'] == 'needs_setup'
        script = ('import sqlite3,ssl,sys,json;'
                  'print(json.dumps({"version":sys.version_info[:3],"executable":sys.executable,"sqlite":sqlite3.sqlite_version,"ssl":ssl.OPENSSL_VERSION}))')
        modules = subprocess.run([str(target/'python/python.exe'), '-I', '-B', '-c', script],
                                 env=env, capture_output=True, encoding='utf-8')
        assert modules.returncode == 0, modules.stderr
        assert json.loads(modules.stdout)['version'] == [3, 14, 10]
    demo = subprocess.run([str(plugin/'skills/post-experiment-knowledge/python/python.exe'), '-I', '-B',
                           str(plugin/'examples/synthetic30.py'), '--output', str(tmp_path/'独立运行的30条归档')],
                          env=env, cwd=tmp_path, capture_output=True, encoding='utf-8')
    assert demo.returncode == 0, demo.stdout+demo.stderr
    result = json.loads(demo.stdout)
    assert result['records'] == 30 and result['all_evidence_verified'] and result['sync_verified']


@pytest.mark.skipif(os.name != 'nt', reason='Windows launcher behavior')
def test_missing_embedded_runtime_reports_incomplete_package_without_fallback(tmp_path):
    source = Path(__file__).parents[1]
    output = tmp_path/'source-only.zip'
    packaging.build_plugin(source, output)
    with zipfile.ZipFile(output) as z:
        z.extractall(tmp_path/'source-only')
    launcher = tmp_path/'source-only/post-experiment-knowledge/skills/post-experiment-knowledge/scripts/expkm.cmd'
    command = f'"{os.environ["ComSpec"]}" /d /s /c ""{launcher}" doctor"'
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, encoding='utf-8')
    assert result.returncode == 2
    assert 'Bundled Python is missing' in result.stderr
