"""A complete post-result demo using synthetic evidence only; never runs a model."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from expkm.common import write_json, atomic_bytes
from expkm.store import Store
from expkm.knowledge import Knowledge, render
from expkm.sync import MarkdownSync, sealed
from expkm.templates import Templates, TemplateRequired, default_template
from expkm.destinations import Destinations, DestinationRequired

def demo(output):
    store = Store(output)
    templates = Templates(store)
    try:
        binding = templates.require('synthetic-quality')
    except TemplateRequired:
        # This demo simulates an explicit user selection using synthetic material only.
        proposal = templates.propose('synthetic-quality', default_template(), 'synthetic-demo-selection')
        binding = templates.confirm('synthetic-quality', proposal, proposal['version'])
    destinations = Destinations(store)
    try:
        destination = destinations.require('synthetic-quality')
    except DestinationRequired:
        proposal = destinations.propose('synthetic-quality', {'mode': 'markdown', 'markdown': {'target': str(store.root/'maintained-report.md'), 'root': str(store.root)}, 'archives': {'scope': 'none'}})
        destination = destinations.confirm('synthetic-quality', proposal, proposal['version'])
    source = store.root/'synthetic-inputs'; source.mkdir(exist_ok=True)
    rows = []
    for i in range(30):
        file = source/f'attempt-{i:02d}.json'
        write_json(file, {'synthetic': True, 'attempt': i, 'score': 0.8})
        meta = {'status': 'completed', 'config': {'rank': 8}, 'metrics': {'score': {'value': 0.8, 'unit': 'ratio', 'direction': 'max', 'definition': 'correct/n', 'denominator': 30}},
                'comparison': {'dataset': 'synthetic-v1', 'split': 'validation', 'protocol': 'paired-v1', 'layer': 'offline', 'aggregation': 'per-round-median'}}
        rows.append(store.record('synthetic-quality', f'actual-attempt-{i:02d}', meta, [file], [source]))
    knowledge = Knowledge(store)
    def draft(subset):
        return {'claims': [{'id': 'baseline', 'question': 'What does this evidence support?', 'text': 'Repeated synthetic evidence supports the baseline within the declared protocol.', 'status': 'candidate',
                            'evidence': [{'record_id': r['record_id'], 'revision': r['revision'], 'sha256': r['evidence'][0]['sha256']} for r in subset]}], 'decisions': [],
                'report_sections': {
                    'overview': [{'type': 'paragraph', 'text': 'Synthetic demonstration of already-produced independent repetitions; no model was run.'}],
                    'environment': [{'type': 'table', 'columns': ['Setting', 'Value'], 'rows': [['rank', 8], ['Execution', 'Synthetic source files only']]}],
                    'data': [{'type': 'table', 'columns': ['Item', 'Value'], 'rows': [['Dataset', 'synthetic-v1'], ['Split', 'validation'], ['Records', 30]]}],
                    'metrics': [{'type': 'table', 'columns': ['Metric', 'Definition / unit', 'Denominator', 'Acceptance'], 'rows': [['score', 'correct/n; ratio', 30, 'No production acceptance claimed']]}],
                    'limitations': [{'type': 'paragraph', 'text': 'Synthetic data validates the archival workflow, not real model quality.'}]}}
    head = knowledge.head('synthetic-quality')
    if head is None:
        head = knowledge.update('synthetic-quality', draft(rows[:1]))
    state = knowledge.update('synthetic-quality', draft(rows), head['version'])
    markdown = render(state); atomic_bytes(store.root/'main-preview.md', markdown.encode('utf-8'))
    index = '# Experiment index\n\n'+'\n'.join(f"- {r['source_key']}: record {r['record_id']} · revision {r['revision']}" for r in rows)
    atomic_bytes(store.root/'experiment-index.md', index.encode('utf-8'))
    sync = MarkdownSync(store.root/'sync')
    adapter, target, roots = destinations.resolve(destination)
    if adapter != 'markdown':
        raise ValueError('Synthetic demo requires its explicitly selected local destination')
    plan = sync.plan(target, markdown, roots)
    del plan['plan_id']
    plan['report_template'] = {'topic': binding['topic'], 'version': binding['version']}
    plan['report_destination'] = {'topic': destination['topic'], 'version': destination['version']}
    sealed(plan); write_json(store.root/'sync-preview.json', plan)
    # Explicit synthetic-demo local apply, not an external/production authorization.
    sync.apply(plan, plan['plan_id'])
    receipt = {'records': len(rows), 'main_result_questions': markdown.count('#### What does this evidence support?'), 'template_version': binding['version'], 'destination_version': destination['version'], 'all_evidence_verified': all(store.verify(r['record_id'])['verified'] for r in rows), 'sync_verified': sync.verify(plan)['verified'], 'model_calls': 0}
    write_json(store.root/'demo-verification.json', receipt)
    return receipt

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True)
    print(json.dumps(demo(p.parse_args().output)))
