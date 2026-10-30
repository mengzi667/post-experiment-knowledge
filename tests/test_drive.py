import json
import subprocess
from pathlib import Path
import pytest
from expkm.common import digest
from expkm.drive import LarkDrive


def runner(raw,rows=None):
    calls=[]
    def run(argv,**kwargs):
        calls.append((argv,kwargs));args=argv[1:]
        assert '--as' in args and args[args.index('--as')+1]=='user'
        assert '--yes' not in args and 'shell' not in kwargs
        if '+upload' in args:
            filename=args[args.index('--file')+1]
            assert not Path(filename).is_absolute()
            assert (Path(kwargs['cwd'])/filename).read_bytes()==raw
            data={'file_token':'synthetic-file'}
        elif 'list' in args:
            data={'files':rows if rows is not None else [{'type':'file','token':'synthetic-file','name':'archive.zip','parent_token':'synthetic-folder'}],'has_more':False}
        else:
            assert '+download' in args
            output=args[args.index('--output')+1];assert not Path(output).is_absolute()
            (Path(kwargs['cwd'])/output).write_bytes(raw);data={}
        return subprocess.CompletedProcess(argv,0,json.dumps({'ok':True,'identity':'user','data':data}).encode(),b'')
    return run,calls


def test_cli_upload_requires_exact_folder_and_write_opt_in(tmp_path):
    raw=b'synthetic bundle';file=tmp_path/(digest(raw)+'.zip');file.write_bytes(raw)
    run,calls=runner(raw);readonly=LarkDrive(['synthetic-folder'],tmp_path/'private',runner=run)
    with pytest.raises(ValueError):readonly.upload(file,'synthetic-folder','archive.zip')
    client=LarkDrive(['synthetic-folder'],tmp_path/'private',True,runner=run)
    with pytest.raises(ValueError):client.upload(file,'unselected-folder','archive.zip')
    assert not calls
    assert client.upload(file,'synthetic-folder','archive.zip')=='synthetic-file'
    assert '--folder-token' in calls[0][0] and '--file-token' not in calls[0][0]


def test_remote_verification_checks_folder_name_size_and_download_hash(tmp_path):
    raw=b'synthetic bytes';run,calls=runner(raw);c=LarkDrive(['synthetic-folder'],tmp_path/'private',runner=run)
    r=c.verify('synthetic-file','synthetic-folder','archive.zip',digest(raw),len(raw))
    assert r and r['verified'] and r['sha256']==digest(raw)
    assert c.verify('synthetic-file','synthetic-folder','archive.zip',digest(b'other'),len(raw))['verified'] is False
    assert c.verify('synthetic-file','synthetic-folder','different.zip',digest(raw),len(raw))['verified'] is False


def test_missing_remote_membership_does_not_download(tmp_path):
    run,calls=runner(b'synthetic',rows=[]);c=LarkDrive(['synthetic-folder'],tmp_path/'private',runner=run)
    r=c.verify('synthetic-file','synthetic-folder','archive.zip',digest(b'synthetic'),9)
    assert r and not r['verified']
    assert not any('+download' in a for a,k in calls)


def test_cli_errors_and_timeouts_do_not_echo_payload_or_retry(tmp_path):
    calls=[]
    def fail(argv,**kwargs):
        calls.append(argv);return subprocess.CompletedProcess(argv,10,b'',b'PRIVATE_RESPONSE_MUST_NOT_ECHO')
    raw=b'synthetic';p=tmp_path/(digest(raw)+'.zip');p.write_bytes(raw)
    c=LarkDrive(['synthetic-folder'],tmp_path/'private',True,runner=fail)
    with pytest.raises(ValueError) as exc:c.upload(p,'synthetic-folder','archive.zip')
    assert 'PRIVATE_RESPONSE' not in str(exc.value) and len(calls)==1 and '--yes' not in calls[0]
    def timeout(argv,**kwargs):raise subprocess.TimeoutExpired(argv,55)
    c=LarkDrive(['synthetic-folder'],tmp_path/'private',True,runner=timeout)
    with pytest.raises(TimeoutError):c.upload(p,'synthetic-folder','archive.zip')

def test_scope_error_is_structured_without_echoing_untrusted_cli_text(tmp_path):
    def missing(argv,**kwargs):
        err={'ok':False,'error':{'subtype':'missing_scope','missing_scopes':['space:document:retrieve'],'message':'PRIVATE_CLI_TEXT'}}
        return subprocess.CompletedProcess(argv,3,b'',json.dumps(err).encode())
    c=LarkDrive(['synthetic-folder'],tmp_path/'private',True,runner=missing)
    raw=b'synthetic';p=tmp_path/(digest(raw)+'.zip');p.write_bytes(raw)
    with pytest.raises(ValueError) as exc:c.upload(p,'synthetic-folder','archive.zip')
    assert getattr(exc.value,'missing_scopes',None)==['space:document:retrieve']
    assert 'PRIVATE_CLI_TEXT' not in str(exc.value)
