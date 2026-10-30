"""Reviewable optimistic sync with durable backups and unknown-outcome reconciliation."""
import base64
import copy
import xml.etree.ElementTree as ET
from pathlib import Path
from .common import atomic_bytes, digest, identifier, lock, no_symlinks, read_json, within, write_json, output_path
from .documents import parse_xml, RESOURCE_TAGS
from .store import Store

class SyncConflict(ValueError):
    pass

def sealed(plan):
    plan['plan_id'] = digest(plan)
    return plan

def authorize(plan, approved):
    if approved != plan.get('plan_id') or digest({k: v for k, v in plan.items() if k != 'plan_id'}) != approved:
        raise ValueError('Explicit approval of the unchanged plan digest required')


def validate_template_ref(plan):
    for name in ['report_template', 'report_destination', 'report_knowledge']:
        if name not in plan:
            continue
        ref = plan[name]
        if not isinstance(ref, dict) or set(ref) != {'topic', 'version'}:
            raise ValueError('Invalid sync template reference')
        identifier(ref['topic']); identifier(ref['version'])
    if 'report_template' in plan and 'report_destination' in plan and plan['report_template']['topic'] != plan['report_destination']['topic']:
        raise ValueError('Sync template and destination must belong to the same topic')
    if 'report_knowledge' in plan and ('report_template' not in plan or plan['report_knowledge']['topic'] != plan['report_template']['topic']):
        raise ValueError('Report knowledge must belong to the same topic')

def signature(xml, include_ids=False):
    nodes = list(parse_xml(xml))
    if len(nodes) != 1:
        raise ValueError('An atomic XML block is required')
    node = nodes[0]
    def one(n):
        return [n.tag, sorted((k, v) for k, v in n.attrib.items() if include_ids or k != 'id'), n.text or '',
                [[one(c), c.tail or ''] for c in n]]
    return digest(one(node))

def resources(xml):
    return [(n.tag, sorted((k, v) for k, v in n.attrib.items() if k != 'id'))
            for n in ET.fromstring(xml).iter() if n.tag in RESOURCE_TAGS]

def b64(raw):
    return base64.b64encode(raw).decode('ascii')

class MarkdownSync:
    def __init__(self, journal):
        self.root = Store(journal).root

    def _target(self, plan):
        required = {'schema_version', 'adapter', 'target', 'allowed_roots', 'existed', 'before', 'after', 'plan_id'}
        if set(plan) - {'report_template', 'report_destination', 'report_knowledge'} != required or plan['schema_version'] != 1 or plan['adapter'] != 'markdown' or not isinstance(plan['existed'], bool):
            raise ValueError('Invalid Markdown plan schema')
        validate_template_ref(plan)
        target = within(plan['target'], plan['allowed_roots'])
        store_root = self.root.parent if self.root.name == 'sync' else self.root
        target = output_path(target, store_root, allow_external=True)
        if target.suffix.lower() not in {'.md', '.markdown'}:
            raise ValueError('Markdown output requires a Markdown filename')
        for key in ['before', 'after']:
            base64.b64decode(plan[key], validate=True)
        return target

    def plan(self, path, content, allowed_roots, region='report'):
        identifier(region); path = within(path, allowed_roots)
        store_root = self.root.parent if self.root.name == 'sync' else self.root
        output_path(path, store_root, allow_external=True)
        if path.suffix.lower() not in {'.md', '.markdown'}:
            raise ValueError('Markdown output requires a Markdown filename')
        raw = path.read_bytes() if path.exists() else b''
        text = raw.decode('utf-8')
        begin, end = f'<!-- expkm:{region}:begin -->', f'<!-- expkm:{region}:end -->'
        if begin in content or end in content:
            raise ValueError('Managed markers cannot appear in content')
        block = begin+'\n'+content.rstrip()+'\n'+end
        if text.count(begin) != text.count(end) or text.count(begin) > 1:
            raise ValueError('Ambiguous managed region')
        if begin in text:
            i, j = text.index(begin), text.index(end)
            if j < i:
                raise ValueError('Invalid managed region order')
            after = text[:i]+block+text[j+len(end):]
        else:
            after = text+('\n' if text and not text.endswith('\n') else '')+block+'\n'
        return sealed({'schema_version': 1, 'adapter': 'markdown', 'target': str(path),
                       'allowed_roots': [str(no_symlinks(r)) for r in allowed_roots],
                       'existed': path.exists(), 'before': b64(raw), 'after': b64(after.encode('utf-8'))})

    def apply(self, plan, approved):
        authorize(plan, approved)
        target = self._target(plan)
        before, after = [base64.b64decode(plan[k]) for k in ['before', 'after']]
        with lock(self.root):
            raw = target.read_bytes() if target.exists() else b''
            if target.exists() and raw == after:
                return {'status': 'already_applied', 'verified': True}
            if raw != before or target.exists() != plan['existed']:
                raise SyncConflict('Markdown changed after preview')
            write_json(self.root/(plan['plan_id']+'.backup.json'), plan)
            atomic_bytes(target, after)
            result = self.verify(plan)
            write_json(self.root/(plan['plan_id']+'.receipt.json'), result)
            return result

    def verify(self, plan):
        authorize(plan, plan['plan_id'])
        target = self._target(plan)
        return {'verified': target.is_file() and target.read_bytes() == base64.b64decode(plan['after']), 'plan_id': plan['plan_id']}

    def rollback(self, plan, approved):
        authorize(plan, approved)
        target = self._target(plan)
        with lock(self.root):
            if not self.verify(plan)['verified']:
                raise SyncConflict('Refusing to roll back changed Markdown')
            if plan['existed']:
                atomic_bytes(target, base64.b64decode(plan['before']))
            else:
                target.unlink()
            return {'restored': True}

class FeishuSync:
    def __init__(self, client, journal):
        self.client, self.root = client, Store(journal).root

    def plan(self, replacements):
        snap = self.client.read(); changes = []; blocks = snap['blocks']
        known = {ET.fromstring(b).get('id'): i for i, b in enumerate(blocks)}
        if not replacements or not set(replacements).issubset(known):
            raise ValueError('Explicit known block replacements required')
        for block_id, after in replacements.items():
            nodes = list(parse_xml(after))
            if len(nodes) != 1 or nodes[0].tag not in {'p', 'h1', 'h2', 'h3', 'h4', 'table', 'blockquote', 'callout'}:
                raise ValueError('One supported atomic replacement block required')
            index = known[block_id]; before = blocks[index]
            if resources(before) != resources(after):
                raise ValueError('Resource or native citation removal/change requires a separate reviewed migration')
            if signature(before) != signature(after):
                changes.append({'index': index, 'before': before, 'after': after})
        plan = {'schema_version': 1, 'adapter': 'feishu', 'target': getattr(self.client, 'document', 'injected-client'),
                'base_revision': snap['revision'], 'before_blocks': blocks, 'changes': changes}
        states = self._states(plan)
        if len({digest(s) for s in states}) != len(states):
            raise ValueError('Cyclic sync plan is ambiguous')
        return sealed(plan)

    def _states(self, plan):
        values = [signature(b) for b in plan['before_blocks']]; states = [list(values)]
        for change in plan['changes']:
            values[change['index']] = signature(change['after']); states.append(list(values))
        return states

    def _position(self, plan, snap):
        current = [signature(b) for b in snap['blocks']]
        states = self._states(plan)
        if current not in states:
            raise SyncConflict('Document differs from every known plan state')
        return states.index(current)

    def _validate(self, plan, approved):
        authorize(plan, approved)
        required = {'schema_version', 'adapter', 'target', 'base_revision', 'before_blocks', 'changes', 'plan_id'}
        if set(plan) - {'report_template', 'report_destination', 'report_knowledge'} != required or plan['schema_version'] != 1 or plan['adapter'] != 'feishu' or plan['target'] != getattr(self.client, 'document', 'injected-client'):
            raise ValueError('Invalid Feishu plan or target')
        validate_template_ref(plan)
        if not isinstance(plan['base_revision'], int) or plan['base_revision'] < 0:
            raise ValueError('Invalid source revision')
        seen = set()
        for change in plan['changes']:
            i = change['index']
            if not isinstance(i, int) or i < 0 or i >= len(plan['before_blocks']) or i in seen:
                raise ValueError('Invalid or repeated block change')
            seen.add(i)
            if signature(change['before'], True) != signature(plan['before_blocks'][i], True) or resources(change['before']) != resources(change['after']):
                raise ValueError('Replacement does not preserve its bound source/resources')
            nodes = list(parse_xml(change['after']))
            if len(nodes) != 1 or nodes[0].tag not in {'p', 'h1', 'h2', 'h3', 'h4', 'table', 'blockquote', 'callout'}:
                raise ValueError('Unsupported replacement')
        states = self._states(plan)
        if len({digest(s) for s in states}) != len(states):
            raise ValueError('Ambiguous sync states')

    def _same_snapshot(self, a, b):
        return a['revision'] == b['revision'] and [signature(x, True) for x in a['blocks']] == [signature(x, True) for x in b['blocks']]

    def _load_state(self, plan, snapshot):
        file = self.root/(plan['plan_id']+'.state.json')
        if file.exists():
            state = read_json(file)
            if state['plan_id'] != plan['plan_id']:
                raise ValueError('Journal binding mismatch')
            return state
        original = {'revision': plan['base_revision'], 'blocks': plan['before_blocks']}
        if not self._same_snapshot(snapshot, original):
            raise SyncConflict('Initial revision or block identity changed after preview')
        return {'plan_id': plan['plan_id'], 'cursor': 0, 'expected': original, 'pending': None}

    def _observe(self, plan, state, snapshot):
        pending = state['pending']
        if not pending:
            if not self._same_snapshot(snapshot, state['expected']):
                raise SyncConflict('Revision or block identity differs from acknowledged state')
            return state
        if self._same_snapshot(snapshot, state['expected']):
            raise TimeoutError('Pending write remains unknown; do not replay without authoritative/operator resolution')
        expected = state['expected']; index = pending['index']
        if len(snapshot['blocks']) != len(expected['blocks']) or snapshot['revision'] <= expected['revision']:
            raise SyncConflict('Unknown source continuity after write')
        if [signature(b) for b in snapshot['blocks']] != self._states(plan)[pending['to_cursor']]:
            raise SyncConflict('Pending operation did not produce the exact planned state')
        if any(signature(a, True) != signature(b, True) for i, (a, b) in enumerate(zip(snapshot['blocks'], expected['blocks'])) if i != index):
            raise SyncConflict('Unrelated block identity changed during write')
        return {'plan_id': plan['plan_id'], 'cursor': pending['to_cursor'], 'expected': snapshot, 'pending': None}

    def _execute(self, plan, approved, direction):
        self._validate(plan, approved)
        state_file = self.root/(plan['plan_id']+'.state.json')
        with lock(self.root):
            write_json(self.root/(plan['plan_id']+'.backup.json'), plan)
            for _ in range(len(plan['changes'])+2):
                snapshot = self.client.read(); state = self._load_state(plan, snapshot)
                if state['pending'] and state['pending']['direction'] != direction:
                    raise TimeoutError('Resolve the pending operation before changing sync direction')
                state = self._observe(plan, state, snapshot); write_json(state_file, state)
                cursor = state['cursor']; goal = len(plan['changes']) if direction == 'apply' else 0
                if cursor == goal:
                    result = {'verified': True, 'plan_id': plan['plan_id'], 'applied': cursor} if direction == 'apply' else {'restored': True}
                    write_json(self.root/(plan['plan_id']+'.receipt.json'), result)
                    return result
                change = plan['changes'][cursor if direction == 'apply' else cursor-1]
                state['pending'] = {'index': change['index'], 'direction': direction, 'to_cursor': cursor+(1 if direction == 'apply' else -1)}
                write_json(state_file, state)
                block_id = ET.fromstring(snapshot['blocks'][change['index']]).get('id')
                self.client.replace(block_id, change['after' if direction == 'apply' else 'before'], snapshot['revision'])
            raise SyncConflict('Unexpected sync state')

    def apply(self, plan, approved):
        return self._execute(plan, approved, 'apply')

    def verify(self, plan):
        self._validate(plan, plan['plan_id']); snap = self.client.read(); state = self._load_state(plan, snap)
        try:
            observed = self._observe(plan, state, snap)
        except TimeoutError:
            return {'verified': False, 'unknown': True, 'plan_id': plan['plan_id']}
        return {'verified': observed['cursor'] == len(plan['changes']), 'plan_id': plan['plan_id']}

    def rollback(self, plan, approved):
        return self._execute(plan, approved, 'rollback')

    def resolve_unknown(self, plan, approved, confirmed_not_applied=False):
        self._validate(plan, approved)
        if not confirmed_not_applied:
            raise ValueError('Independent operator confirmation is required')
        with lock(self.root):
            snap = self.client.read(); state = self._load_state(plan, snap)
            if not state['pending'] or not self._same_snapshot(snap, state['expected']):
                raise SyncConflict('Cannot confirm an operation in a different state')
            state['pending'] = None; state['resolution'] = 'operator_independently_confirmed_not_applied'
            write_json(self.root/(plan['plan_id']+'.state.json'), state)
            return {'resolved': True, 'replayed': False}
