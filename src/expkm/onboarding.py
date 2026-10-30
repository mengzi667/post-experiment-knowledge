"""Stage-aware introduction and minimal missing-information cards."""
from .common import identifier, read_json
from .templates import Templates, TemplateRequired
from .destinations import Destinations
from .selections import Selections, SelectionRequired

INTRODUCTION = '''本插件在实验结束后归档证据、维护研究结论并保存报告，不执行实验。提供已有结果或历史记录，说明希望归档、分析、保存报告，或全部完成；Agent 按目标选择步骤，只询问当前步骤缺少的信息，已确认设置可复用。

```text
研究专题
├── 专题主报告：当前结论、关键结果、适用边界与决策
├── 实验索引：实验列表、配置差异、状态及档案入口
└── 完整实验档案
    ├── 原始证据：结果、配置、日志及产物引用
    └── 追溯记录：实验 ID、版本、哈希及结论证据关系
```

这是按需生成的三层视图。可只归档或只分析；保存报告时才确认模板和报告位置。原始证据默认留在私有本地目录，明确选择上传范围和目录后才上传。'''


def setup_status(store, topic, stage='workflow', sync_kind='report'):
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
    if stage == 'workflow':
        questions.append({'id':'outcome', 'required':True,
                          'title':'本次希望完成什么？目标已说明时直接选择相应步骤，无需再问。',
                          'options':['完整整理：归档、分析并保存报告','仅归档已有结果','仅分析和维护结论','仅保存已有报告或上传档案']})
    if stage == 'record':
        try:
            Selections(store, 'record-location').require(topic)
        except SelectionRequired:
            questions.append({'id':'record_location','required':True,
                              'title':'实验原始证据和追溯记录保存到哪个私有本地目录？请提供路径；可确认使用当前建议目录。'})
    if stage == 'sync' and sync_kind in {'report','both'}:
        try:
            template = Templates(store).require(topic)
        except TemplateRequired:
            questions.append({'id':'template','required':True, 'title':'本专题采用哪份报告模板？',
                              'options':['使用已有模板（提供文档或文件）','先查看并确认一份新模板']})
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
            'introduction':INTRODUCTION, 'questions':questions,
            'suggested_record_location':str(store.root), 'default_personal_space':personal_space,
            'preference_warning':preference_warning,
            'template_version':template['version'] if template else None,
            'destination_version':destination['version'] if destination else None,
            'location_followup':'Ask only unresolved details for the requested stage. Reuse explicit choices in context. A known goal selects stages directly; workflow cards only clarify an ambiguous goal. Selection never grants remote write permission.'}
