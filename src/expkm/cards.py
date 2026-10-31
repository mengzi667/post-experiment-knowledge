"""Durable one-question-at-a-time handoff to the host's native card tool.

This tracks explicit host replies, not human identity or actual UI rendering.
Only metadata belongs here; experiment payloads remain behind the intake gate.
"""
import json
from .common import canonical,digest,identifier,read_json,write_json,lock

class CardsRequired(ValueError):
    pass

class Cards:
    def __init__(self,store):
        self.store=store;self.root=store.root/'cards'

    def _questions(self,items):
        if not isinstance(items,list) or not items:raise ValueError('Provide required questions')
        value=json.loads(canonical(items));seen=set()
        for q in value:
            if not isinstance(q,dict) or set(q)-{'id','title','options','required'} or not {'id','title'}<=set(q):
                raise ValueError('Invalid card question')
            identifier(q['id'])
            if q['id'] in seen or not isinstance(q['title'],str) or not q['title'].strip():raise ValueError('Unique question identity and title required')
            seen.add(q['id'])
            if 'required' in q and q['required'] is not True:raise ValueError('Only necessary questions enter the required queue')
            if 'options' in q:
                options=q['options']
                if not isinstance(options,list) or not 2<=len(options)<=4 or not all(isinstance(x,str) and x.strip() for x in options) or len(set(options))!=len(options):
                    raise ValueError('Provide two to four distinct choices, or omit options for text input')
        return value

    def _path(self,session):
        identifier(session);return self.root/(session+'.json')

    def _load(self,session):
        value=read_json(self._path(session))
        if value['session']!=session or digest({k:v for k,v in value.items() if k!='version'})!=value['version']:
            raise ValueError('Card state changed outside the protocol')
        return value

    def _save(self,value):
        value={k:v for k,v in value.items() if k!='version'};value['version']=digest(value)
        write_json(self._path(value['session']),value);return value

    def _not_bound(self,value):
        if (self.store.root/'intake/requests'/(value['request_id']+'.json')).exists():
            raise ValueError('Request already confirmed; use a new request for changes')
        if value['closed']:raise ValueError('Card session closed; use a new request')

    def start(self,request_id,questions):
        identifier(request_id);items=self._questions(questions)
        session=digest({'request_id':request_id})
        with lock(self.store.root):
            path=self._path(session)
            if path.exists():
                value=self._load(session)
                if value['questions']!=items:raise ValueError('Existing request questions differ; resume or use a new request')
                return self.status(session)
            value={'schema_version':1,'session':session,'request_id':request_id,'questions':items,'answers':[], 'closed':False}
            self._not_bound(value);self._save(value)
        return self.status(session)

    def status(self,session):
        value=self._load(session);count=len(value['answers'])
        return {'session':session,'request_id':value['request_id'],'answered':count,
                'remaining':len(value['questions'])-count,'closed':value['closed'],
                'complete':count==len(value['questions']),'execution_allowed':False}

    def next(self,session):
        value=self._load(session);result=self.status(session)
        if result['closed']:raise ValueError('Card session closed')
        if result['complete']:return {**result,'status':'complete','questions':[]}
        q=value['questions'][len(value['answers'])]
        return {**result,'status':'needs_user_answer','question_id':q['id'],
                'questions':[{k:q[k] for k in ['title','options'] if k in q}]}

    def answer(self,session,response):
        if not isinstance(response,dict) or set(response)!={'question_id','answer','response_reference'}:
            raise ValueError('Use an actual host reply with its question and response reference')
        if not all(isinstance(v,str) and v.strip() for v in response.values()):raise ValueError('An unanswered or preselected card is not a reply')
        with lock(self.store.root):
            value=self._load(session);self._not_bound(value)
            prior=next((a for a in value['answers'] if a['question_id']==response['question_id']),None)
            if prior:
                if prior!=response:raise ValueError('Conflicting reply; review a new request instead of overwriting')
                return self.status(session)
            if len(value['answers'])>=len(value['questions']) or value['questions'][len(value['answers'])]['id']!=response['question_id']:
                raise ValueError('Reply must match the single pending question')
            value['answers'].append(json.loads(canonical(response)));self._save(value)
        return self.status(session)

    def append(self,session,questions):
        items=self._questions(questions)
        with lock(self.store.root):
            value=self._load(session);self._not_bound(value)
            if len(value['answers'])!=len(value['questions']):raise ValueError('Finish the pending question before adding follow-ups')
            if {q['id'] for q in items}&{q['id'] for q in value['questions']}:raise ValueError('Question identity already used')
            value['questions'].extend(items);self._save(value)
        return self.status(session)

    def close(self,session):
        with lock(self.store.root):
            value=self._load(session)
            if len(value['answers'])!=len(value['questions']):raise CardsRequired('Pending answers must be resolved before closing')
            value['closed']=True;self._save(value)
        return self.status(session)

    def require_complete(self,request_id):
        session=digest({'request_id':request_id});path=self._path(session)
        if path.exists() and not self.status(session)['complete']:
            raise CardsRequired('Resume the single pending card; unanswered questions cannot be skipped')
