"""Evidence-checked Agent drafts; never schedules follow-up experiments."""
import json
import math
from collections import defaultdict
from .common import canonical, digest, identifier, lock, read_json, within, write_json
from .templates import Templates, TemplateRequired, validate_binding, validate_blocks

def compare(a, b, metric, changed_variables=()):
    left, right = a['metadata'], b['metadata']
    result = {'comparability': 'direct', 'reasons': [], 'differences': {},
              'metric_effect': 'not_assessed', 'decision_changed': False}
    reasons = result['reasons']
    if any(r.get('status') != 'completed' for r in [left, right]):
        reasons.append('Results are not both completed'); result['comparability'] = 'insufficient'
    for key in ['dataset', 'split', 'protocol', 'layer', 'aggregation']:
        x, y = left.get('comparison', {}).get(key), right.get('comparison', {}).get(key)
        if not all(isinstance(v, str) and v.strip() and v.strip().lower() not in {'unknown', 'n/a', 'missing'} for v in [x, y]):
            result['comparability'] = 'insufficient'; reasons.append('Missing comparison identity: '+key)
        elif x != y:
            result['comparability'] = 'incompatible'; reasons.append('Different '+key)
    x, y = left.get('metrics', {}).get(metric), right.get('metrics', {}).get(metric)
    if not isinstance(x, dict) or not isinstance(y, dict):
        result['comparability'] = 'insufficient'; reasons.append('Metric definition unavailable'); return result
    for key in ['unit', 'direction', 'definition', 'denominator']:
        vals = [x.get(key), y.get(key)]
        valid = all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) and v > 0 for v in vals) if key == 'denominator' else all(isinstance(v, str) and v.strip() and v.strip().lower() not in {'unknown', 'n/a', 'missing'} for v in vals)
        if not valid:
            result['comparability'] = 'insufficient'; reasons.append('Missing metric identity: '+key)
        elif x[key] != y[key]:
            result['comparability'] = 'incompatible'; reasons.append('Different metric '+key)
    for scope in ['config', 'environment']:
        for key in set(left.get(scope, {})) | set(right.get(scope, {})):
            u, v = left.get(scope, {}).get(key), right.get(scope, {}).get(key)
            if u != v:
                name = scope+'.'+key; result['differences'][name] = [u, v]
                if name not in changed_variables and result['comparability'] == 'direct':
                    result['comparability'] = 'conditional'; reasons.append('Uncontrolled difference: '+name)
    values = [x.get('value'), y.get('value')]
    if not all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
        result['comparability'] = 'insufficient'; reasons.append('Missing or nonnumeric measurement'); return result
    if result['comparability'] in {'direct', 'conditional'} and x['direction'] in {'min', 'max'}:
        delta = values[1] - values[0]; result['delta'] = delta
        result['metric_effect'] = 'unchanged' if delta == 0 else ('improved' if delta * (1 if x['direction'] == 'max' else -1) > 0 else 'regressed')
    return result

class Knowledge:
    def __init__(self, store):
        self.store = store

    def update(self, topic, draft, expected_version=None):
        identifier(topic)
        binding = Templates(self.store).require(topic)
        # Copy caller input, reject nonfinite values, keep user/Agent judgment explicit.
        draft = json.loads(canonical(draft)); claims = draft.get('claims', [])
        if set(draft) - {'claims', 'decisions', 'reason', 'report_sections'}:
            raise ValueError('Unknown or reserved knowledge draft fields')
        validate_blocks(binding['definition'], draft.get('report_sections', {}))
        if not claims:
            raise ValueError('A structured Agent draft with evidence is required')
        ids = set()
        for claim in claims:
            identifier(claim['id'])
            if claim['id'] in ids or not claim.get('question') or not claim.get('text') or not claim.get('evidence'):
                raise ValueError('Claims need unique identity, question, text and evidence')
            ids.add(claim['id'])
            if claim.get('status') not in {'candidate', 'confirmed', 'disputed', 'superseded'}:
                raise ValueError('Explicit review state required')
            cited = set()
            for ref in claim['evidence']:
                row = self.store.get(ref['record_id'], ref['revision'])
                if row['topic'] != topic:
                    raise ValueError('Evidence belongs to a different topic')
                entries = [e for e in row['evidence'] if e['sha256'] == ref['sha256']]
                if not entries:
                    raise ValueError('Unverifiable evidence reference')
                raw = within(self.store.root/entries[0]['object'], [self.store.root/'objects']).read_bytes()
                if digest(raw) != ref['sha256']:
                    raise ValueError('Evidence integrity failure')
                if ref.get('quote') and ref['quote'] not in raw.decode('utf-8-sig', errors='replace'):
                    raise ValueError('Quoted evidence not present')
                cited.add((ref['record_id'], ref['revision']))
            for assertion in claim.get('assertions', []):
                if (assertion['record_id'], assertion['revision']) not in cited:
                    raise ValueError('Numeric assertion must cite its record')
                value = self.store.get(assertion['record_id'], assertion['revision'])
                try:
                    for key in assertion['path']:
                        value = value[key]
                except (KeyError, TypeError, IndexError) as exc:
                    raise ValueError('Assertion path not present') from exc
                if canonical(value) != canonical(assertion['value']):
                    raise ValueError('Asserted value differs from source')
        for decision in draft.get('decisions', []):
            identifier(decision['id'])
            if not decision.get('text') or not decision.get('claim_ids') or not set(decision['claim_ids']).issubset(ids):
                raise ValueError('Decision must reference verified draft claims')
        folder = self.store.root/'knowledge'/topic
        with lock(self.store.root):
            if Templates(self.store).require(topic)['version'] != binding['version']:
                raise ValueError('Template changed while preparing the report')
            old = self.head(topic)
            if (old['version'] if old else None) != expected_version:
                raise ValueError('Knowledge changed since this draft was prepared')
            if old:
                by_id = {c['id']: c for c in claims}
                changed = any(c['id'] not in by_id or any(c.get(k) != by_id[c['id']].get(k) for k in ['text', 'status', 'question']) for c in old['claims'])
                changed = (changed or old.get('decisions') != draft.get('decisions', [])
                           or old.get('report_sections', {}) != draft.get('report_sections', {})
                           or old.get('report_template', {}).get('version') != binding['version'])
                if changed and not draft.get('reason'):
                    raise ValueError('Conclusion, report content or template revision requires a reason')
                # Omission does not silently erase old claims.
                if not {c['id'] for c in old['claims']}.issubset(ids):
                    raise ValueError('Retain omitted claims as explicitly superseded')
            value = {'schema_version': 1, 'topic': topic, **draft,
                     'report_template': binding,
                     'validation_scope': 'references, integrity and structured assertions; semantic correctness needs review'}
            version = digest(value); value['version'] = version
            write_json(folder/(version+'.json'), value)
            versions = read_json(folder/'history.json') if (folder/'history.json').exists() else []
            if version not in versions:
                versions.append(version)
            write_json(folder/'history.json', versions); write_json(folder/'head.json', {'version': version})
        return value

    def head(self, topic):
        identifier(topic); folder = self.store.root/'knowledge'/topic
        if not (folder/'head.json').exists():
            return None
        version = read_json(folder/'head.json')['version']; identifier(version)
        value = read_json(folder/(version+'.json'))
        if digest({k: v for k, v in value.items() if k != 'version'}) != version:
            raise ValueError('Knowledge integrity mismatch')
        return value

    def history(self, topic):
        identifier(topic); folder = self.store.root/'knowledge'/topic
        values = []
        for version in read_json(folder/'history.json'):
            identifier(version); value = read_json(folder/(version+'.json'))
            if digest({k: v for k, v in value.items() if k != 'version'}) != version:
                raise ValueError('Knowledge integrity mismatch')
            values.append(value)
        return values

    def trace(self, topic, claim_id):
        return next(c for c in self.head(topic)['claims'] if c['id'] == claim_id)

def render(state):
    if not state.get('report_template'):
        raise TemplateRequired(state.get('topic'))
    binding = validate_binding(state['report_template'], state['topic'])
    content = state.get('report_sections', {})
    validate_blocks(binding['definition'], content)
    questions = defaultdict(list)
    for claim in state['claims']:
        if claim['status'] != 'superseded':
            questions[claim['question']].append(claim)
    lines = ['# '+state['topic'], '', '私有报告预览；未提供、未测或未验收不代表通过。']
    def table(columns, rows):
        def cell(value):
            return str(value).replace('|', '&#124;').replace('\r', '').replace('\n', '<br>')
        return ['| '+' | '.join(map(cell, columns))+' |', '| '+' | '.join('---' for _ in columns)+' |'] + ['| '+' | '.join(map(cell, row))+' |' for row in rows]
    def emit(node, level):
        if node['title']:
            lines.extend(['', '#'*level+' '+node['title']])
        blocks = content.get(node['id'], [])
        for block in blocks:
            lines.append('')
            if block['type'] == 'paragraph':
                lines.append(block['text'])
            elif block['type'] == 'list':
                lines.extend('- '+text for text in block['items'])
            else:
                lines.extend(table(block['columns'], block['rows']))
        if not blocks and 'columns' in node:
            lines.append('')
            lines.extend(table(node['columns'], [[field]+['未提供']*(len(node['columns'])-1) for field in node['fields']]))
        if node['role'] == 'results':
            for question, claims in questions.items():
                lines.extend(['', '#'*min(level+1, 6)+' '+question])
                for claim in claims:
                    count = len({e['record_id'] for e in claim['evidence']})
                    lines.extend(['', claim['text'], f"\n[{claim['status']}] Evidence: {count} records · claim {claim['id']}"])
        elif node['role'] == 'decisions':
            for decision in state.get('decisions', []):
                lines.extend(['', decision['text'], '\n支撑结论：'+', '.join(decision['claim_ids'])])
            if not state.get('decisions') and not blocks:
                lines.extend(['', '尚未形成已记录的决策。'])
        elif node['role'] == 'evidence':
            lines.extend(['', '完整实验明细保留在独立档案中。按结论 ID 使用 trace 获取记录版本与原始证据哈希。',
                          '\n模板：'+binding['definition']['name']+' · '+binding['version']])
        elif not blocks and not node.get('children') and 'columns' not in node:
            lines.extend(['', '未提供。'])
        for child in node.get('children', []):
            emit(child, level+1)
    for node in binding['definition']['sections']:
        emit(node, 2)
    return '\n'.join(lines)+'\n'
