"""Per-request metadata confirmation before CLI access to experiment payloads.

This verifies explicit CLI confirmation and scope, not human identity/UI exposure.
Trusted low-level library primitives remain callable by authorized application code.
"""
import json
from pathlib import Path
from .common import canonical,digest,identifier,read_json,write_json,lock,no_symlinks,display_path
from .templates import Templates
from .selections import Selections
from .destinations import Destinations


class IntakeRequired(ValueError):
    def __init__(self,message,reason='missing_confirmation'):
        if reason not in {'missing_confirmation','request_closed','scope_mismatch','settings_changed'}:
            raise ValueError('Invalid confirmation status')
        self.reason=reason
        super().__init__(message)


class Intakes:
    def __init__(self,store):
        self.store=store
        self.root=store.root/'intake'

    def _definition(self,definition):
        value=json.loads(canonical(definition))
        required={'request_id','topic','goal','scope','requirements','stages','source_roots',
                  'all_topic_records','reports','archives'}
        if set(value)-{'max_archive_bytes','mlflow_runs','phase'} != required:
            raise ValueError('Provide request identity, goal, scope, requirements and explicit inputs/outputs')
        phase=value.setdefault('phase','execution')
        if phase not in {'execution','template-recommendation'}:
            raise ValueError('Invalid intake phase')
        identifier(value['request_id']);identifier(value['topic'])
        for key in ['goal','scope']:
            if not isinstance(value[key],str) or not value[key].strip():
                raise ValueError('Goal and scope must be explicit')
        if not isinstance(value['requirements'],list) or not value['requirements'] or not all(isinstance(x,str) and x.strip() for x in value['requirements']):
            raise ValueError('State the request requirements before execution')
        for key,choices in [('stages',{'record','synthesize','sync'}),('reports',{'markdown','feishu'})]:
            items=value[key]
            if not isinstance(items,list) or len(set(items))!=len(items) or not set(items)<=choices:
                raise ValueError('Invalid requested stages or report outputs')
        if not value['stages'] or not isinstance(value['all_topic_records'],bool):
            raise ValueError('Explicit stages and topic scope required')
        if not isinstance(value['source_roots'],list):
            raise ValueError('Explicit input roots required')
        roots=[]
        for root in value['source_roots']:
            if not isinstance(root,str) or not Path(root).is_absolute():
                raise ValueError('Input roots must be absolute user-selected paths')
            roots.append(display_path(no_symlinks(root)))
        value['source_roots']=roots
        if 'mlflow_runs' in value:
            if not isinstance(value['mlflow_runs'],list):
                raise ValueError('Explicit MLflow Run identities required')
            for run in value['mlflow_runs']:identifier(run)
        if not roots and not value['all_topic_records'] and not value.get('mlflow_runs'):
            raise ValueError('Provide selected inputs or explicitly include existing topic records')
        if value['archives'] not in {'none','trace','full'}:
            raise ValueError('Explicit archive scope required')
        if (value['reports'] or value['archives']!='none') and 'sync' not in value['stages']:
            raise ValueError('Publishing needs the Sync stage')
        if ('synthesize' in value['stages'] or value['archives']!='none') and not value['all_topic_records']:
            raise ValueError('Current topic synthesis/export includes all topic records; subset scope is unsupported')
        budget=value.get('max_archive_bytes',100_000_000)
        if not isinstance(budget,int) or isinstance(budget,bool) or not 1<=budget<=1_000_000_000:
            raise ValueError('Archive size limit must be an explicit bounded integer')
        if value['archives']!='none':
            value['max_archive_bytes']=budget
        elif 'max_archive_bytes' in value:
            raise ValueError('No archive size limit without requested archive output')
        return value

    def _bindings(self,definition):
        topic=definition['topic']
        template=Templates(self.store).require(topic) if definition['phase']=='execution' else None
        local=Selections(self.store,'record-location').require(topic)
        refs={'store':display_path(self.store.root),'template_version':template['version'] if template else None,
              'record_location_version':local['version']}
        if definition['reports']:
            destination=Destinations(self.store).require(topic)
            mode=destination['definition']['mode']
            selected=['markdown','feishu'] if mode=='both' else [mode]
            if set(selected)!=set(definition['reports']):
                raise ValueError('Report outputs differ from the selected exact destinations')
            refs['destination_version']=destination['version']
        if definition['archives']!='none':
            archive=Selections(self.store,'archive-destination').require(topic)
            if archive['definition']['archives']['scope']!=definition['archives']:
                raise ValueError('Archive scope differs from its exact selected parent')
            refs['archive_destination_version']=archive['version']
        return refs

    def propose(self,definition):
        definition=self._definition(definition)
        value={'schema_version':1,'definition':definition,'bindings':self._bindings(definition)}
        return {**value,'version':digest(value)}

    def _validate(self,value):
        if not isinstance(value,dict) or set(value)!={'schema_version','definition','bindings','version'} or value['schema_version']!=1:
            raise ValueError('Invalid intake')
        if value['definition']!=self._definition(value['definition']) or digest({k:v for k,v in value.items() if k!='version'})!=value['version']:
            raise ValueError('Request changed after review')
        if value['bindings']!=self._bindings(value['definition']):
            raise IntakeRequired('Template, location or upload scope changed; reconfirm this request','settings_changed')
        return value

    def confirm(self,proposal,approved):
        value=json.loads(canonical(self._validate(proposal)))
        if approved!=value['version']:
            raise ValueError('Confirm the exact reviewed requirements summary')
        with lock(self.store.root):
            from .cards import Cards
            Cards(self.store).require_complete(value['definition']['request_id'])
            if (self.root/'closed'/(value['version']+'.json')).exists():
                raise IntakeRequired('Closed requests cannot be reopened','request_closed')
            request=self.root/'requests'/(value['definition']['request_id']+'.json')
            if request.exists() and read_json(request)['version']!=value['version']:
                raise ValueError('Use a new request identity for a changed request')
            write_json(self.root/'confirmed'/(value['version']+'.json'),value)
            write_json(request,{'version':value['version']})
        return value

    def require(self,version,stage,topic=None):
        if version is None:
            raise IntakeRequired('Confirm this request, template and exact output locations first')
        identifier(version)
        file=self.root/'confirmed'/(version+'.json')
        if not file.exists():
            raise IntakeRequired('A proposal or previous preference is not a confirmed request')
        value=self._validate(read_json(file))
        if value['version']!=version:raise ValueError('Intake version mismatch')
        if (self.root/'closed'/(version+'.json')).exists():
            raise IntakeRequired('Closed request; confirm a new request','request_closed')
        definition=value['definition']
        if definition['phase']=='template-recommendation':
            allowed=stage=='recommend-template'
        else:
            allowed=stage in definition['stages']
        if not allowed or (topic is not None and definition['topic']!=topic):
            raise IntakeRequired('Operation is outside this confirmed request','scope_mismatch')
        return value

    def close(self,version):
        identifier(version)
        path=self.root/'confirmed'/(version+'.json')
        if not path.exists():raise IntakeRequired('Unknown request')
        with lock(self.store.root):
            write_json(self.root/'closed'/(version+'.json'),{'version':version,'closed':True})
        return {'closed':True,'version':version}
