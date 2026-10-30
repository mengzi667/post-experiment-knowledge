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
