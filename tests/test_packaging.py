from pathlib import Path
import shutil
import zipfile
import pytest
from expkm.packaging import build_plugin,install_skill

def test_release_is_allowlisted_and_excludes_private_files(tmp_path):
    source=Path(__file__).parents[1]
    # Deliberate unlisted synthetic canary under a copied tree, never real data.
    copy=tmp_path/'source';shutil.copytree(source,copy,ignore=shutil.ignore_patterns('__pycache__','.pytest_cache','.venv','*.egg-info'))
    (copy/'private-customer-result.json').write_text('SYNTHETIC_PRIVATE_CANARY_DO_NOT_DISTRIBUTE')
    out=tmp_path/'release.zip'; result=build_plugin(copy,out)
    assert result and result['verified']
    with zipfile.ZipFile(out) as z:
        assert any(n.endswith('plugin.json') for n in z.namelist())
        assert not any('private-customer' in n for n in z.namelist())
        assert all(b'SYNTHETIC_PRIVATE_CANARY_DO_NOT_DISTRIBUTE' not in z.read(n) for n in z.namelist())

def test_install_is_self_contained_and_does_not_overwrite_existing_skill(tmp_path):
    source=Path(__file__).parents[1];dest=tmp_path/'skills'/'post-experiment-knowledge'
    result=install_skill(source,dest)
    assert result and (dest/'runtime'/'expkm'/'cli.py').exists()
    (dest/'SKILL.md').write_text('User modification')
    with pytest.raises(ValueError):install_skill(source,dest)

def test_clean_plugin_extraction_can_launch_without_source_checkout_or_pip(tmp_path):
    import json,subprocess,sys,os
    source=Path(__file__).parents[1];out=tmp_path/'release.zip';build_plugin(source,out)
    unpack=tmp_path/'unpacked'
    with zipfile.ZipFile(out) as z:z.extractall(unpack)
    plugin=unpack/'post-experiment-knowledge'
    env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'}
    result=subprocess.run([sys.executable,str(plugin/'skills/post-experiment-knowledge/scripts/expkm.py'),'--store',str(tmp_path/'private'),'setup','--topic','synthetic'],cwd=tmp_path,capture_output=True,encoding='utf-8',env=env)
    assert result.returncode==0,result.stderr
    value=json.loads(result.stdout)
    assert value['status']=='needs_setup' and [q['id'] for q in value['questions']]==['requirements','template','record_location','outcome']
    catalog=json.loads((plugin/'.agents/plugins/marketplace.json').read_text())
    assert catalog['plugins'][0]['source']['path']=='./'
