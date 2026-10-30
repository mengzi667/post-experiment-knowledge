"""Local-only primitives; no experiment or network operations."""
import contextlib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()

def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', value):
        raise ValueError('Invalid identifier')
    return value

def private_default():
    base = Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local'/'share'))
    return base/'PostExperimentKnowledge'/'projects'

def no_symlinks(path):
    path = Path(path).absolute()
    if os.name == 'nt' and not str(path).startswith('\\\\?\\'):
        raw = str(path)
        path = Path('\\\\?\\UNC\\'+raw[2:] if raw.startswith('\\\\') else '\\\\?\\'+raw)
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError('Symlink paths are not accepted')
    # Windows junctions are reparse points too, even when is_symlink is false.
    if os.name == 'nt':
        for p in [path, *path.parents]:
            if p.exists() and getattr(p.lstat(), 'st_file_attributes', 0) & 0x400:
                raise ValueError('Reparse paths are not accepted')
    return path.resolve()

def display_path(path):
    value = str(path)
    if value.startswith('\\\\?\\UNC\\'):
        return '\\\\'+value[8:]
    return value[4:] if value.startswith('\\\\?\\') else value

def within(path, roots):
    resolved = no_symlinks(path)
    if not any(resolved.is_relative_to(no_symlinks(r)) for r in roots):
        raise ValueError('Path outside authorized roots')
    return resolved

def output_path(path, store_root, allow_external=False):
    """Separate mutable exports from immutable evidence, knowledge and journals."""
    path, root = no_symlinks(path), no_symlinks(store_root)
    if path.is_relative_to(no_symlinks(Path(__file__).resolve().parents[2])):
        raise ValueError('Private output cannot target distributable code')
    if path.is_relative_to(root):
        relative = path.relative_to(root)
        reserved = {'objects', 'records', 'knowledge', 'templates', 'destinations', 'bundles', 'archive-sync', 'incoming', 'sync', 'lark', 'lark-drive', 'index.sqlite3', '.writer.lock'}
        if not relative.parts or relative.parts[0] in reserved:
            raise ValueError('Output targets reserved private state')
    elif not allow_external:
        raise ValueError('Output outside private store')
    return path

def atomic_bytes(path, raw):
    path = no_symlinks(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.write-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def write_json(path, value):
    atomic_bytes(path, canonical(value))

def read_json(path):
    return json.loads(no_symlinks(path).read_text(encoding='utf-8-sig'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))

@contextlib.contextmanager
def lock(root):
    path = no_symlinks(Path(root)/'.writer.lock')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('a+b') as stream:
        stream.seek(0); stream.write(b'0'); stream.flush(); stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError('Private store is busy') from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
