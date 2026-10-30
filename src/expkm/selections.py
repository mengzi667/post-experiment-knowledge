"""Stage-specific private selections; confirmation does not grant remote writes."""
import json
from .common import canonical, digest, identifier, lock, read_json, write_json, display_path
from .destinations import Destinations, DestinationRequired


class SelectionRequired(ValueError):
    def __init__(self, kind, topic):
        self.kind, self.topic = kind, topic
        super().__init__('Confirm the selection needed for the current stage')


class Selections:
    def __init__(self, store, kind):
        if kind not in {'record-location', 'archive-destination'}:
            raise ValueError('Unknown stage selection')
        self.store, self.kind = store, kind

    def _definition(self, definition):
        value = json.loads(canonical(definition))
        if self.kind == 'record-location':
            if value != {'store': display_path(self.store.root)}:
                raise ValueError('Local archive selection must match this private store')
        else:
            policy = value.get('archives', {})
            location = 'wiki' if 'wiki' in policy else 'folder'
            if set(value) != {'archives'} or policy.get('scope') not in {'none', 'trace', 'full'}:
                raise ValueError('Choose an explicit archive scope')
            if set(policy) != ({'scope'} if policy['scope'] == 'none' else {'scope', location}):
                raise ValueError('Choose one exact archive parent')
            if policy['scope'] != 'none':
                identifier(policy[location])
        return value

    def propose(self, topic, definition):
        value = {'schema_version': 1, 'kind': self.kind, 'topic': identifier(topic),
                 'definition': self._definition(definition)}
        return {**value, 'version': digest(value)}

    def _validate(self, value, topic):
        if (set(value) != {'schema_version','kind','topic','definition','version'}
                or value['schema_version'] != 1 or value['kind'] != self.kind
                or value['topic'] != identifier(topic)
                or value['definition'] != self._definition(value['definition'])
                or digest({k:v for k,v in value.items() if k != 'version'}) != value['version']):
            raise ValueError('Stage selection changed after review')
        return value

    def get(self, topic, version):
        identifier(topic); identifier(version)
        path = self.store.root/self.kind/topic/(version+'.json')
        if path.exists():
            value = self._validate(read_json(path), topic)
            if value['version'] != version:
                raise ValueError('Stage selection history mismatch')
            return value
        # Existing report/archive plans remain recoverable after an upgrade.
        if self.kind == 'archive-destination':
            return Destinations(self.store).get(topic, version)
        raise SelectionRequired(self.kind, topic)

    def require(self, topic):
        identifier(topic)
        head = self.store.root/self.kind/topic/'head.json'
        if head.exists():
            return self.get(topic, read_json(head)['version'])
        # Grandfather only a user's confirmed, complete legacy workflow setup.
        try:
            legacy = Destinations(self.store).require(topic)
            if self.kind == 'archive-destination':
                if 'archives' not in legacy['definition']:
                    raise SelectionRequired(self.kind, topic)
                return legacy
            from .templates import Templates
            Templates(self.store).require(topic)
            return self.propose(topic, {'store': display_path(self.store.root)})
        except (DestinationRequired, SelectionRequired):
            raise SelectionRequired(self.kind, topic) from None
        except Exception as exc:
            from .templates import TemplateRequired
            if isinstance(exc, TemplateRequired):
                raise SelectionRequired(self.kind, topic) from None
            raise

    def confirm(self, topic, proposal, approved, expected_version=None):
        value = self._validate(json.loads(canonical(proposal)), topic)
        if approved != value['version']:
            raise ValueError('Explicit confirmation of the exact selection is required')
        folder = self.store.root/self.kind/topic
        with lock(self.store.root):
            # A new stage-specific selection may replace a legacy fallback.
            old = self.get(topic, read_json(folder/'head.json')['version']) if (folder/'head.json').exists() else None
            if (old['version'] if old else None) != expected_version:
                raise ValueError('Selection changed; review the current version')
            write_json(folder/(value['version']+'.json'), value)
            write_json(folder/'head.json', {'version':value['version']})
        return value
