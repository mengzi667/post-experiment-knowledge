import io
import zipfile

import pytest
from expkm.archives import check_payload


@pytest.mark.parametrize('source,name', [
    ("import os\nconfig.api_key=os.environ['SERVICE_TOKEN']\n", 'launch.py'),
    ("import os\napi_key=os.getenv('SERVICE_TOKEN')\n", 'launch.py'),
    ('header=f"Authorization: Bearer {TOKEN}\\r\\nX-Budget: {budget}\\r\\n"', 'probe.py'),
    ("info={'api_key':'secret-must-not-leak'}", 'test_probe.py'),
    ("writer.write(\"api_key='private-service-token' port=12345\\n\")", 'test_writer.py'),
    ("api_key='[REDACTED]'", 'record.txt'),
])
def test_dynamic_code_and_explicit_masking_do_not_count_as_hardcoded_credentials(source, name):
    try:
        check_payload(source.encode(), filename=name)
    except (TypeError, ValueError) as exc:
        pytest.fail(f'Context-aware scanning incorrectly blocked this non-secret case: {type(exc).__name__}')


@pytest.mark.parametrize('source,name', [
    ('api_key=UNREVIEWED_CREDENTIAL_VALUE', 'result.txt'),
    ('{"api_key":"UNREVIEWED_CREDENTIAL_VALUE"}', 'result.json'),
    ("api_key='UNREVIEWED_CREDENTIAL_VALUE'", 'test_probe.py'),
    ("import os\napi_key=os.environ['TOKEN']; password='UNREVIEWED_CREDENTIAL_VALUE'", 'launch.py'),
    ("import os\napi_key=os.getenv('TOKEN', 'UNREVIEWED_CREDENTIAL_VALUE')", 'launch.py'),
    ('Authorization: Bearer UNREVIEWED_CREDENTIAL_VALUE', 'result.log'),
    ('a sample with accesstoken: UNREVIEWED_CREDENTIAL_VALUE', 'input.jsonl'),
    ('a sample with '+('sk-'+'A'*40), 'test_probe.py'),
])
def test_unknown_literals_and_sample_credentials_remain_blocked(source, name):
    with pytest.raises(ValueError, match='credential'):
        check_payload(source.encode(), filename=name)


def test_compressed_evidence_cannot_hide_credentials():
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('input.jsonl','{"text":"accesstoken: UNREVIEWED_CREDENTIAL_VALUE"}')
    with pytest.raises(ValueError, match='credential'):
        check_payload(stream.getvalue(), filename='results.zip')
