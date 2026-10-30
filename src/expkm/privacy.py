"""Conservative credential checks with static code context; never execute inputs."""
import ast
import io
from pathlib import PurePath
import re
import zipfile

STRONG = re.compile(rb'AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:sk-|ghp_|github_pat_|hf_)[A-Za-z0-9_-]{20,}')
ASSIGNMENT = re.compile(rb'(?i)(?<![A-Za-z0-9_])["\x27]?(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)["\x27]?\s*[:=]\s*["\x27]?(?P<value>[^\s"\x27,}]{8,})')
BEARER = re.compile(rb'(?i)authorization\s*:\s*bearer\s+(?P<value>\S+)')
MASKS = {b'[REDACTED]', b'<REDACTED>', b'[MASKED]', b'<MASKED>', b'********'}
TEST_MARKERS = {b'private-service-token', b'secret-must-not-leak'}


def _code_ranges(raw, filename):
    if not filename or not str(filename).lower().endswith('.py'):
        return [], [], []
    try:
        tree = ast.parse(raw.decode('utf-8-sig'))
    except (ValueError, SyntaxError, UnicodeError):
        return [], [], []
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1]+len(line))
    def span(n):
        return offsets[n.lineno-1]+n.col_offset, offsets[n.end_lineno-1]+n.end_col_offset
    dynamic, joined, literals = [], [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            joined.append(span(node))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(span(node))
        value = node.value if isinstance(node, (ast.Assign, ast.AnnAssign)) else None
        if value is None:
            continue
        env_subscript = (isinstance(value, ast.Subscript) and isinstance(value.value, ast.Attribute)
                         and isinstance(value.value.value, ast.Name) and value.value.value.id == 'os'
                         and value.value.attr == 'environ')
        env_call = (isinstance(value, ast.Call) and not value.keywords and len(value.args) == 1
                    and isinstance(value.func, ast.Attribute)
                    and ((isinstance(value.func.value, ast.Name) and value.func.value.id == 'os' and value.func.attr == 'getenv')
                         or (isinstance(value.func.value, ast.Attribute) and isinstance(value.func.value.value, ast.Name)
                             and value.func.value.value.id == 'os' and value.func.value.attr == 'environ' and value.func.attr == 'get')))
        if env_subscript or env_call:
            dynamic.append(span(value))
    return dynamic, joined, literals


def check_payload(raw, filename=None, _depth=0, _budget=None):
    """Reject potential credentials, retaining no values in errors or normal logs."""
    if _budget is None:
        _budget = [100_000_000]
    if STRONG.search(raw):
        raise ValueError('Potential credential in archival payload; inspect privately before export')
    dynamic, joined, literals = _code_ranges(raw, filename)
    test_file = bool(filename and PurePath(str(filename).replace('\\', '/')).name.startswith('test_'))
    def inside(position, ranges):
        return any(start <= position < end for start, end in ranges)
    for regex in (ASSIGNMENT, BEARER):
        for match in regex.finditer(raw):
            value = match['value']
            if value.upper() in MASKS:
                continue
            if inside(match.start('value'), dynamic):
                continue
            if test_file and value in TEST_MARKERS and inside(match.start(), literals):
                continue
            if (regex is BEARER and inside(match.start(), joined)
                    and re.match(rb'^\{[A-Za-z_][A-Za-z0-9_]*\}(?:\\[rnt]|$)', value)):
                continue
            raise ValueError('Potential credential in archival payload; inspect privately before export')
    if raw.startswith(b'PK') and zipfile.is_zipfile(io.BytesIO(raw)):
        if _depth >= 3:
            raise ValueError('Nested credential inspection limit reached; inspect privately')
        with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
            for info in zipped.infolist():
                _budget[0] -= info.file_size
                if _budget[0] < 0:
                    raise ValueError('Compressed credential inspection limit reached; inspect privately')
                check_payload(zipped.read(info), filename=info.filename, _depth=_depth+1, _budget=_budget)
