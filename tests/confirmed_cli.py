"""Explicit synthetic-user intake fixtures for existing command behavior tests."""
from pathlib import Path
from expkm.cli import parser,run
from expkm.intake import Intakes
from expkm.templates import Templates,TemplateRequired
from expkm.selections import Selections,SelectionRequired
from expkm.destinations import Destinations,DestinationRequired
from expkm.common import digest,display_path


def approved_args(store,args):
    args=list(map(str,args))
    if not args:return args
    command=args[0]
    protected={'record','capture-mlflow','synthesize','compare','organize','report-preview','trace','reindex'}
    if command in {'sync','archive'} and args[1]!='verify':protected.add(command)
    if command not in protected:return args
    topic=args[args.index('--topic')+1] if '--topic' in args else 'quality'
    if command=='compare':topic=store.get(args[args.index('--left')+1])['topic']
    if command in {'sync','archive'} and '--plan' in args:
        from expkm.common import read_json
        plan=read_json(args[args.index('--plan')+1])
        topic=plan.get('topic') or plan.get('report_template',{}).get('topic','quality')
    try:
        Templates(store).require(topic)
        # This fixture represents an explicit synthetic user's local directory choice.
        try:Selections(store,'record-location').require(topic)
        except SelectionRequired:
            choice=Selections(store,'record-location')
            p=choice.propose(topic,{'store':display_path(store.root)});choice.confirm(topic,p,p['version'])
    except TemplateRequired:return args
    reports=[];archives='none'
    try:
        d=Destinations(store).require(topic);mode=d['definition']['mode']
        reports=['markdown','feishu'] if mode=='both' else [mode]
    except DestinationRequired:pass
    try:archives=Selections(store,'archive-destination').require(topic)['definition']['archives']['scope']
    except SelectionRequired:pass
    definition={'request_id':'synthetic-fixture','topic':topic,'goal':'Exercise the explicitly selected synthetic behavior',
                'scope':'Synthetic fixture directory and existing topic evidence','requirements':['Preserve source fixtures','No experiment execution'],
                'stages':['record','synthesize','sync'],'source_roots':[display_path(store.root.parent)],
                'all_topic_records':True,'reports':reports,'archives':archives}
    if archives!='none':definition['max_archive_bytes']=100_000_000
    p=Intakes(store).propose(definition)
    definition['request_id']='synthetic-'+digest(p['bindings'])[:24]
    p=Intakes(store).propose(definition);Intakes(store).confirm(p,p['version'])
    return ['--intake',p['version'],*args]


def run_confirmed(store,*args):
    return run(parser().parse_args(['--store',str(store.root),*approved_args(store,args)]))
