"""Lossless document inventories. Classification is an Agent-reviewed input."""
import hashlib
import re
import xml.etree.ElementTree as ET
from collections import Counter

RESOURCE_TAGS = {'img', 'source', 'whiteboard', 'sheet', 'bitable', 'base_refer', 'synced_reference', 'cite'}

def parse_xml(xml):
    if '<!DOCTYPE' in xml.upper() or '<!ENTITY' in xml.upper():
        raise ValueError('XML declarations with external/entity definitions are not accepted')
    root = ET.fromstring('<root>' + xml + '</root>')
    if len(root) == 1 and root[0].tag in {'document', 'fragment', 'doc'}:
        root = root[0]
    return root

def inventory(xml):
    root = parse_xml(xml)
    blocks, section, ids = [], [], set()
    for index, node in enumerate(root):
        text = ''.join(node.itertext())
        if re.fullmatch(r'h[1-9]', node.tag):
            level = int(node.tag[1])
            section = section[:level - 1] + [text]
        block_id = node.get('id') or f'position-{index:06d}'
        if block_id in ids:
            raise ValueError('Duplicate source block identity')
        ids.add(block_id)
        blocks.append({'id': block_id, 'position': index, 'tag': node.tag,
                       'section': list(section), 'text': text,
                       'xml': ET.tostring(node, encoding='unicode'),
                       'numbers': re.findall(r'[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?', text),
                       'cells': [''.join(c.itertext()) for c in node.iter() if c.tag in {'td', 'th'}],
                       'resources': [{'tag': c.tag, **c.attrib} for c in node.iter() if c.tag in RESOURCE_TAGS],
                       'suggested_destination': 'review'})
    counts = Counter(b['text'] for b in blocks if b['text'])
    return {'source_sha256': hashlib.sha256(xml.encode()).hexdigest(), 'blocks': blocks,
            'tables': sum(len(list(n.iter('table'))) for n in root),
            'exact_duplicates': [{'text': t, 'count': n} for t, n in counts.items() if n > 1],
            'note': 'Structural diagnostics only; no automatic semantic relocation.'}

def migration_preview(xml, mapping, main_markdown):
    inv = inventory(xml)
    ids = {b['id'] for b in inv['blocks']}
    if not mapping or {m['block_id'] for m in mapping} != ids:
        raise ValueError('Every source block must have a destination, with no unknown blocks')
    for m in mapping:
        if m.get('destination') not in {'main', 'index', 'archive', 'review'} or not m.get('reason') or not m.get('question'):
            raise ValueError('Explicit question, reason and destination required')
    return {'coverage': 1.0, 'source_sha256': inv['source_sha256'], 'mapping': mapping,
            'archive_xml': xml, 'main_markdown': main_markdown,
            'resources_preserved': True, 'apply_authorized': False,
            'review_pending': sum(m['destination'] == 'review' for m in mapping)}
