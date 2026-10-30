import pytest
from expkm.documents import inventory, migration_preview

XML = '<title id="t">Synthetic topic</title><h1 id="h">Results</h1><p id="p">Recall 90%, n=30.</p><table id="tb"><tbody><tr><td><p>0</p></td></tr></tbody></table><img id="im" token="synthetic-image"/>'

def test_inventory_preserves_atomic_blocks_numbers_and_resources():
    result = inventory(XML)
    assert result and len(result['blocks']) == 5
    assert result['blocks'][2]['numbers'] == ['90', '30']
    assert result['blocks'][3]['cells'] == ['0']
    assert result['blocks'][4]['resources'][0]['token'] == 'synthetic-image'

def test_mapping_covers_every_block_and_archive_is_lossless():
    inv = inventory(XML)
    assert inv
    mapping = [{'block_id': b['id'], 'destination': 'archive', 'question': 'quality', 'reason': 'preserve original'} for b in inv['blocks']]
    result = migration_preview(XML, mapping, '# Current conclusion\n\nEvidence retained.')
    assert result and result['coverage'] == 1.0
    assert result['archive_xml'] == XML
    assert result['resources_preserved']

def test_missing_or_unknown_mapping_blocks_are_rejected():
    with pytest.raises(ValueError):
        migration_preview(XML, [], '# Draft')
    inv = inventory(XML)
    assert inv
    mapping = [{'block_id': b['id'], 'destination': 'archive', 'question': 'quality', 'reason': 'preserve'} for b in inv['blocks']]
    mapping.append({'block_id': 'invented', 'destination': 'main', 'question': 'quality', 'reason': 'wrong'})
    with pytest.raises(ValueError):
        migration_preview(XML, mapping, '# Draft')

def test_nested_resource_and_duplicate_paragraph_diagnostics_are_not_auto_migration():
    result = inventory('<p id="a">same</p><p id="b">same</p><callout id="c"><p><cite type="doc" doc-id="synthetic-doc"/></p></callout>')
    assert result and result['exact_duplicates']
    assert result['blocks'][2]['resources'][0]['doc-id'] == 'synthetic-doc'
    assert all(b['suggested_destination'] == 'review' for b in result['blocks'])
