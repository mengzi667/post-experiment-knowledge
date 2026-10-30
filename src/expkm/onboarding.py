"""Presentation data for an introduction followed by optional selection cards."""
from .common import identifier, read_json
from .templates import Templates, TemplateRequired
from .destinations import Destinations

INTRODUCTION = '''本插件在实验结束后归档证据、维护研究结论并保存报告，不执行实验。提供已有结果或历史记录，首次确认模板、保存位置和上传范围，后续按专题复用。

```text
研究专题
├── 专题主报告：当前结论、关键结果、适用边界与决策
├── 实验索引：实验列表、配置差异、状态及档案入口
└── 完整实验档案
    ├── 原始证据：结果、配置、日志及产物引用
    └── 追溯记录：实验 ID、版本、哈希及结论证据关系
```

报告可保存到本地 Markdown、飞书或两者。原始证据和追溯默认保留本地，只有明确选择上传范围及归档目录后才会上传；不会进入插件分发包。'''


def setup_status(store, topic):
    identifier(topic); questions = []
    from .common import private_default
    preference_file = private_default().parent/'preferences.json'
    preferences = read_json(preference_file) if preference_file.exists() else {}
    personal_space = preferences.get('personal_space')
    if personal_space is not None:
        from urllib.parse import urlsplit
        value = urlsplit(personal_space['url'])
        identifier(personal_space['node_token'])
        if personal_space.get('confirmed_by_user') is not True or value.scheme != 'https' or value.path.rstrip('/') != '/wiki/'+personal_space['node_token']:
            raise ValueError('Private personal-space preference needs explicit confirmation and a valid Wiki URL')
    try:
        template = Templates(store).require(topic)
    except TemplateRequired:
        template = None
        questions.append({'id': 'template', 'title': '本专题采用哪份报告模板？', 'options': ['使用已有模板（提供文档或文件）', '先查看并确认一份新模板']})
    head = store.root/'destinations'/topic/'head.json'
    destination = Destinations(store).get(topic, read_json(head)['version']) if head.exists() else None
    if destination is None:
        questions.append({'id': 'save_method', 'title': '可阅读报告保存到哪里？', 'options': ['仅飞书', '本地 Markdown', '本地 Markdown＋飞书']})
    if destination is None or 'archives' not in destination['definition']:
        questions.append({'id': 'archive_scope', 'title': '除报告外，需要向飞书上传哪些档案？', 'options': ['不上传档案，仅保存报告', '上传追溯档案', '上传原始证据＋追溯档案']})
    if destination is None:
        questions.append({'id': 'save_location', 'required': True,
                          'title': '请提供本次保存结果的具体位置：飞书目标文档或目录链接；本地 Markdown 的目标文件路径。两者都保存时请分别提供。'})
    return {'status': 'needs_setup' if questions else 'ready', 'introduction': INTRODUCTION, 'questions': questions,
            'default_personal_space': personal_space,
            'template_version': template['version'] if template else None, 'destination_version': destination['version'] if destination else None,
            'location_followup': 'Require a concrete user-provided report URL/parent or local filename before reading results; never infer a tenant, personal space or Drive root. Reuse only previously confirmed topic locations. Collect template source and any missing archive directory, then preview exact selections before confirmation.'}
