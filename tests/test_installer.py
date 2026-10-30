import json
import os
from pathlib import Path
import zipfile

import pytest
import expkm.packaging as packaging


def test_release_has_full_file_manifest_and_offline_install_entrypoint(tmp_path):
    out=tmp_path/'release.zip';packaging.build_plugin(Path(__file__).parents[1],out)
    with zipfile.ZipFile(out) as z:
        prefix='post-experiment-knowledge/'
        assert prefix+'release-manifest.json' in z.namelist(), 'An install manifest is required'
        assert prefix+'install.cmd' in z.namelist()
        manifest=json.loads(z.read(prefix+'release-manifest.json'))
        assert {prefix+e['path'] for e in manifest['entries']}==set(z.namelist())-{prefix+'release-manifest.json'}


def test_install_rejects_tampered_package_before_codex_is_called(tmp_path):
    import importlib.util
    assert importlib.util.find_spec('expkm.installer'), 'Offline installer is missing'
    from expkm.installer import install_release
    out=tmp_path/'release.zip';packaging.build_plugin(Path(__file__).parents[1],out)
    with zipfile.ZipFile(out) as z:z.extractall(tmp_path/'unpack')
    source=tmp_path/'unpack/post-experiment-knowledge';(source/'README.md').write_text('tampered')
    calls=[]
    with pytest.raises(ValueError,match='checksum'):
        install_release(source,tmp_path/'installed',codex='codex.exe',runner=lambda *a,**k:calls.append(a))
    assert not calls and not (tmp_path/'installed').exists()


def test_install_is_repeatable_and_never_overwrites_modified_existing_files(tmp_path):
    import importlib.util
    assert importlib.util.find_spec('expkm.installer'), 'Offline installer is missing'
    from expkm.installer import install_release
    out=tmp_path/'release.zip';packaging.build_plugin(Path(__file__).parents[1],out)
    with zipfile.ZipFile(out) as z:z.extractall(tmp_path/'unpack')
    source=tmp_path/'unpack/post-experiment-knowledge';dest=tmp_path/'installed';calls=[]
    class Success:
        returncode=0
        stdout='{"ok":true}'
        stderr=''
    def runner(args,**kwargs):calls.append(args);return Success()
    first=install_release(source,dest,codex='codex.exe',runner=runner)
    assert first['installed'] and first['reused_existing'] is False
    assert os.path.samefile(calls[0][4],dest.parent), 'Marketplace root must stay stable across version directories'
    catalog=json.loads((dest.parent/'.agents/plugins/marketplace.json').read_text(encoding='utf-8'))
    assert catalog['plugins'][0]['source']['path']=='./installed'
    assert calls[1][3]=='post-experiment-knowledge@'+catalog['name']
    second=install_release(source,dest,codex='codex.exe',runner=runner)
    assert second['reused_existing'] is True
    assert calls[0][1:4]==['plugin','marketplace','add']
    (dest/'README.md').write_text('user change')
    with pytest.raises(ValueError,match='checksum'):
        install_release(source,dest,codex='codex.exe',runner=runner)
    assert (dest/'README.md').read_text()=='user change'


def test_version_upgrade_reuses_marketplace_without_touching_user_records(tmp_path):
    import shutil
    from expkm.installer import install_release
    original=Path(__file__).parents[1]
    source=tmp_path/'source'
    shutil.copytree(original,source,ignore=shutil.ignore_patterns('.git','__pycache__','.pytest_cache'))
    class Success:
        returncode=0; stdout='{}'; stderr=''
    runner=lambda *a,**k:Success()
    def release(version):
        for name in ['plugin.json','.codex-plugin/plugin.json']:
            path=source/name; obj=json.loads(path.read_text());obj['version']=version
            path.write_text(json.dumps(obj))
        out=tmp_path/(version+'.zip');packaging.build_plugin(source,out)
        unpack=tmp_path/version
        with zipfile.ZipFile(out) as z:z.extractall(unpack)
        return unpack/'post-experiment-knowledge'
    a=release('0.5.0-beta.1');b=release('0.6.0-beta.1')
    root=tmp_path/'marketplace';old=root/'0.5.0-beta.1'
    install_release(a,old,codex='codex.exe',runner=runner)
    private=tmp_path/'private-evidence.txt';private.write_text('SYNTHETIC_PRIVATE_HISTORY')
    original_manifest=(old/'release-manifest.json').read_bytes()
    new=root/'0.6.0-beta.1';result=install_release(b,new,codex='codex.exe',runner=runner)
    catalog=json.loads((root/'.agents/plugins/marketplace.json').read_text())
    assert result['version']=='0.6.0-beta.1'
    assert catalog['plugins'][0]['source']['path']=='./0.6.0-beta.1'
    assert (old/'release-manifest.json').read_bytes()==original_manifest
    assert private.read_text()=='SYNTHETIC_PRIVATE_HISTORY'
