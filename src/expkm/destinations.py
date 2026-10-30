"""Private, explicit report destinations. Selection never performs a sync."""
import json
from pathlib import Path
from .common import canonical, digest, identifier, lock, read_json, write_json, within, output_path, display_path, no_symlinks


class DestinationRequired(ValueError):
    def __init__(self, topic=None):
        self.topic = topic
        super().__init__('Select and confirm the report save method and location')


class DestinationTargetRequired(ValueError):
    pass


class Destinations:
    def __init__(self, store):
        self.store = store

    def propose(self, topic, definition):
        identifier(topic)
        value = {'schema_version': 1, 'topic': topic, 'definition': self._definition(definition)}
        value['version'] = digest(value)
        return value

    def _definition(self, definition, allow_legacy=False):
        definition = json.loads(canonical(definition))
        if not isinstance(definition, dict) or definition.get('mode') not in {'markdown', 'feishu', 'both'}:
            raise ValueError('Supported save methods are markdown, feishu and both')
        mode = definition['mode']
        keys = {'mode'} | ({'markdown'} if mode in {'markdown', 'both'} else set()) | ({'feishu'} if mode in {'feishu', 'both'} else set())
        if not allow_legacy or 'archives' in definition:
            keys.add('archives')
        if set(definition) != keys:
            raise ValueError('Provide exactly the locations for the selected save method')
        if 'markdown' in definition:
            item = definition['markdown']
            if not isinstance(item, dict) or set(item) != {'target', 'root'} or not all(isinstance(x, str) and x.strip() and Path(x).is_absolute() for x in item.values()):
                raise ValueError('Explicit absolute Markdown target and authorized root required')
            target = output_path(within(item['target'], [item['root']]), self.store.root, allow_external=True)
            root = no_symlinks(item['root'])
            if target.suffix.lower() not in {'.md', '.markdown'} or (root.exists() and not root.is_dir()):
                raise ValueError('A Markdown filename and directory root are required')
            definition['markdown'] = {'target': display_path(target), 'root': display_path(root)}
        if 'feishu' in definition:
            item = definition['feishu']
            if not isinstance(item, dict) or set(item) != {'document'}:
                raise ValueError('Bind an existing Feishu document; folder creation is a separate operation')
            identifier(item['document'])
        if 'archives' in definition:
            item = definition['archives']
            if not isinstance(item, dict) or item.get('scope') not in {'none', 'trace', 'full'}:
                raise ValueError('Explicitly choose none, trace or full archival upload')
            location = 'wiki' if 'wiki' in item else 'folder'
            expected = {'scope'} if item['scope'] == 'none' else {'scope', location}
            if set(item) != expected:
                raise ValueError('Choose exactly one explicit Drive folder or Wiki archive parent')
            if item['scope'] != 'none':
                identifier(item[location])
        return definition

    def _validate(self, value, topic):
        if not isinstance(value, dict) or set(value) != {'schema_version', 'topic', 'definition', 'version'} or value['schema_version'] != 1 or value['topic'] != identifier(topic):
            raise ValueError('Invalid destination binding')
        if self._definition(value['definition'], allow_legacy=True) != value['definition'] or digest({k: v for k, v in value.items() if k != 'version'}) != value['version']:
            raise ValueError('Destination changed after review')
        return value

    def confirm(self, topic, proposal, approved, expected_version=None):
        value = json.loads(canonical(self._validate(proposal, topic)))
        self._definition(value['definition'])
        if approved != value['version']:
            raise ValueError('Explicit confirmation of the unchanged destination version required')
        folder = self.store.root/'destinations'/topic
        with lock(self.store.root):
            old = self.get(topic, read_json(folder/'head.json')['version']) if (folder/'head.json').exists() else None
            if (old['version'] if old else None) != expected_version:
                raise ValueError('Save method changed; review the current selection first')
            write_json(folder/(value['version']+'.json'), value)
            write_json(folder/'head.json', {'version': value['version']})
        return value

    def get(self, topic, version):
        identifier(topic); identifier(version)
        value = read_json(self.store.root/'destinations'/topic/(version+'.json'))
        if value['version'] != version:
            raise ValueError('Destination history binding mismatch')
        return self._validate(value, topic)

    def require(self, topic):
        identifier(topic)
        head = self.store.root/'destinations'/topic/'head.json'
        if not head.exists():
            raise DestinationRequired(topic)
        value = self.get(topic, read_json(head)['version'])
        if 'archives' not in value['definition']:
            raise DestinationRequired(topic)
        return value

    def resolve(self, binding, adapter=None, target=None, roots=()):
        definition = self._validate(binding, binding['topic'])['definition']
        if adapter is None:
            if definition['mode'] == 'both':
                raise DestinationTargetRequired('Plan each selected adapter separately, then verify both receipts')
            adapter = definition['mode']
        if adapter not in definition or adapter not in {'markdown', 'feishu'}:
            raise ValueError('Adapter differs from the confirmed save method')
        selected = definition[adapter]
        if adapter == 'markdown':
            if target is not None and no_symlinks(target) != no_symlinks(selected['target']):
                raise ValueError('Target differs from the confirmed report location')
            if roots and (len(roots) != 1 or no_symlinks(roots[0]) != no_symlinks(selected['root'])):
                raise ValueError('Authorized root differs from the confirmed report location')
            return adapter, selected['target'], [Path(selected['root'])]
        if (target is not None and target != selected['document']) or roots:
            raise ValueError('Target differs from the confirmed Feishu document')
        return adapter, selected['document'], []
