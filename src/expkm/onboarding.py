"""Stage-aware introduction and minimal missing-information cards."""
from .common import identifier, read_json
from .templates import Templates, TemplateRequired
from .destinations import Destinations
from .selections import Selections, SelectionRequired

INTRODUCTION = '''本插件在实验结束后归档证据、维护研究结论并保存报告，不执行实验。每次新请求先问清目标、范围和要求，确认用户提供或明确指定的模板，以及具体保存位置，再按目标选择步骤。已有偏好可预填本次确认单，不自动授权新任务。

```text
研究专题
├── 专题主报告：当前结论、关键结果、适用边界与决策
├── 实验索引：实验列表、配置差异、状态及档案入口
└── 完整实验档案
    ├── 原始证据：结果、配置、日志及产物引用
    └── 追溯记录：实验 ID、版本、哈希及结论证据关系
```

这是按需生成的三层视图。正式执行必须确认模板和具体保存位置。也可选择由 Codex 推荐模板：先确认需求、范围和位置，只读查看必要材料，展示推荐后再确认模板。能选择的问题优先使用原生选项卡，路径、链接和特殊要求使用卡片中的文本输入。预选不代表作答。'''


def setup_status(store, topic, stage='workflow', sync_kind='report', intake_version=None):
    identifier(topic); questions = []
    if stage not in {'workflow','record','synthesize','sync'} or sync_kind not in {'report','archive','both'}:
        raise ValueError('Unknown requested stage')
    from .common import private_default
    preference_file = private_default().parent/'preferences.json'
    personal_space = None; preference_warning = False
    try:
        preferences = read_json(preference_file) if preference_file.exists() else {}
        personal_space = preferences.get('personal_space')
        if personal_space is not None:
            from urllib.parse import urlsplit
            value = urlsplit(personal_space['url'])
            identifier(personal_space['node_token'])
            if personal_space.get('confirmed_by_user') is not True or value.scheme != 'https' or value.path.rstrip('/') != '/wiki/'+personal_space['node_token']:
                raise ValueError('Invalid optional preference')
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        personal_space = None; preference_warning = True
    template = destination = None
    confirmed=None
    if intake_version is not None:
        from .intake import Intakes
        selected=stage
        if stage=='workflow':
            identifier(intake_version)
            definition=read_json(store.root/'intake'/'confirmed'/(intake_version+'.json'))['definition']
            selected='recommend-template' if definition['phase']=='template-recommendation' else definition['stages'][0]
        confirmed=Intakes(store).require(intake_version,selected,topic)
    if confirmed is None:
        questions.append({'id':'requirements','required':True,
                          'title':'请先确认本次目标、资料范围、交付物和限制要求；已有信息会汇总展示，确认后才开始处理。',
                          'options':['确认本次汇总的需求与要求','补充或调整需求、范围与限制']})
    try:
        template=Templates(store).require(topic)
    except TemplateRequired:
        questions.append({'id':'template','required':True,'title':'请提供或明确指定本次必须使用的模板（链接、文件或已提供的结构）。',
                          'options':['提供已有模板链接或文件','明确沿用此前提供的模板','由 Codex 根据本次实验推荐模板，展示后由我确认']})
    try:
        Selections(store,'record-location').require(topic)
    except SelectionRequired:
        questions.append({'id':'record_location','required':True,
                          'title':'请提供结果与追溯档案保存的具体私有本地目录；不能只选择平台或使用未确认的默认路径。'})
    if stage == 'workflow' and confirmed is None:
        questions.append({'id':'outcome', 'required':True,
                          'title':'本次希望完成什么？目标已说明时直接选择相应步骤，无需再问。',
                          'options':['完整整理：归档、分析并保存报告','仅归档已有结果','仅分析和维护结论','仅保存已有报告或上传档案']})
    if stage == 'sync' and sync_kind in {'report','both'}:
        head = store.root/'destinations'/topic/'head.json'
        destination = Destinations(store).get(topic, read_json(head)['version']) if head.exists() else None
        if destination is None:
            questions.extend([
                {'id':'save_method','required':True,'title':'可阅读报告保存到哪里？',
                 'options':['仅飞书','本地 Markdown','本地 Markdown＋飞书']},
                {'id':'save_location','required':True,
                 'title':'请提供报告的具体位置：飞书文档或目录链接、本地 Markdown 文件路径；两者都保存时请分别提供。'}])
    if stage == 'sync' and sync_kind in {'archive','both'}:
        try:
            archive = Selections(store, 'archive-destination').require(topic)
            if archive['definition']['archives']['scope'] == 'none':
                raise SelectionRequired('archive-destination', topic)
        except SelectionRequired:
            questions.extend([
                {'id':'archive_scope','required':True,'title':'本次向飞书上传哪些档案？',
                 'options':['上传原始证据＋追溯档案','仅上传追溯档案','不上传档案']},
                {'id':'archive_location','required':True,
                 'title':'请选择档案的飞书目标目录或知识库节点链接；选择不上传时无需提供。'}])
    return {'status':'needs_setup' if questions else 'ready', 'stage':stage,
            'execution_allowed':confirmed is not None and confirmed['definition']['phase']=='execution' and not questions,
            'recommendation_read_allowed':confirmed is not None and confirmed['definition']['phase']=='template-recommendation',
            'introduction':INTRODUCTION, 'questions':questions,
            'card_protocol':{'questions_per_call':1,'durable_queue':'cards start|next|answer|append|status|close',
                             'advance_only_after_actual_reply':True,'resume_pending_on_partial_reply':True},
            'suggested_record_location':str(store.root), 'default_personal_space':personal_space,
            'preference_warning':preference_warning,
            'template_version':template['version'] if template else None,
            'destination_version':destination['version'] if destination else None,
            'location_followup':'Before experiment payload reads, clarify this request and show its requirements, mandatory template and all exact save locations. Use native choice cards and free-text fields. Preferences may prefill the summary, never authorize a new request. Confirm an intake, then pass its explicit version to each processing command. Platform write authorization stays separate.'}
