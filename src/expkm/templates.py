"""Frozen, explicitly selected report structures. Templates are data, never code."""
import json
from .common import canonical, digest, identifier, lock, read_json, write_json


class TemplateRequired(ValueError):
    def __init__(self, topic=None):
        self.topic = topic
        super().__init__('Select and confirm a report template before continuing')


def default_template():
    """An optional generic proposal, never an implicitly confirmed default."""
    def node(key, title, role, **extra):
        return {'id': key, 'title': title, 'role': role, **extra}
    def table(key, title, role, columns, fields):
        return node(key, title, role, columns=columns, fields=fields)
    return {'schema_version': 1, 'name': '通用测试报告模板', 'sections': [
        table('report_info', '', 'metadata', ['项目', '填写内容'], ['报告名称 / 编号 / 版本', '测试对象 / 时间', '编写 / 复核 / 状态']),
        node('overview', '1. 测试概述', 'overview'),
        node('design', '2. 测试设计', 'design', children=[
            table('environment', '2.1 方案与环境', 'environment', ['配置项', '基线方案', '候选方案', '差异备注'],
                  ['方案与对象', '版本 / 构建', '关键变更', '硬件', '操作系统 / 运行时', '软件与依赖', '部署位置 / 副本', '调用入口', '关键参数']),
            node('data_execution', '2.2 数据与执行', 'custom', children=[
                table('data', '数据配置', 'data', ['数据项', '填写内容'], ['来源', '版本 / 哈希', '规模与构成', '抽样 / 纳入 / 排除', '划分与隔离', '输入与预处理', '参考答案与复核']),
                table('execution', '执行配置', 'execution', ['执行项', '填写内容'], ['方式与顺序', '负载与并发', '预热与缓存', '重复次数与时长', '测量边界', '超时 / 重试 / 中止', '回退 / 恢复 / 停止', '采样与日志'])]),
            table('metrics', '2.3 指标与验收', 'metrics', ['指标', '含义 / 计算方法 / 单位', '汇总方式 / 分层', '验收口径'], ['待填写指标'])]),
        node('results', '3. 测试结果', 'custom', children=[
            node('main_results', '3.1 主要结果', 'results'),
            node('integrity', '3.2 执行完整性与异常', 'integrity')]),
        node('analysis', '4. 分析与限制', 'custom', children=[
            node('interpretation', '4.1 结果解释', 'analysis'),
            node('limitations', '4.2 适用边界', 'limitations')]),
        node('decisions', '5. 决策与后续', 'decisions'),
        node('evidence', '附录：复现与证据', 'evidence')]}


def sections(definition):
    for section in definition['sections']:
        yield from _walk(section)


def _walk(node):
    yield node
    for child in node.get('children', []):
        yield from _walk(child)


def validate_definition(definition):
    if not isinstance(definition, dict) or set(definition) != {'schema_version', 'name', 'sections'} or definition['schema_version'] != 1:
        raise ValueError('Invalid template definition')
    if not isinstance(definition['name'], str) or not definition['name'].strip() or not isinstance(definition['sections'], list) or not definition['sections']:
        raise ValueError('Template needs a name and sections')
    ids, roles = set(), []
    def check(node, depth):
        if depth > 4 or len(ids) >= 100 or not isinstance(node, dict) or set(node) - {'id', 'title', 'role', 'children', 'columns', 'fields'}:
            raise ValueError('Invalid template section')
        identifier(node['id'])
        if node['id'] in ids or not isinstance(node['title'], str) or '\n' in node['title']:
            raise ValueError('Unique section IDs and single-line headings required')
        ids.add(node['id']); roles.append(node['role'])
        if node['role'] not in {'metadata', 'overview', 'design', 'environment', 'data', 'execution', 'metrics', 'results', 'integrity', 'analysis', 'limitations', 'decisions', 'evidence', 'custom'}:
            raise ValueError('Unknown semantic section role')
        for key in ['columns', 'fields']:
            if key in node and (not isinstance(node[key], list) or not node[key] or not all(isinstance(s, str) and s.strip() for s in node[key])):
                raise ValueError('Table fields and columns must be nonempty strings')
        if ('columns' in node) != ('fields' in node):
            raise ValueError('Table columns and fields must be paired')
        if not isinstance(node.get('children', []), list):
            raise ValueError('Children must be sections')
        for child in node.get('children', []):
            check(child, depth+1)
    for node in definition['sections']:
        check(node, 1)
    if roles.count('results') != 1 or roles.count('decisions') != 1 or roles.count('evidence') != 1:
        raise ValueError('Exactly one results, decisions and evidence section required')


def validate_binding(value, topic=None):
    required = {'schema_version', 'topic', 'definition', 'source', 'version'}
    if not isinstance(value, dict) or set(value) != required or value['schema_version'] != 1:
        raise ValueError('Invalid frozen template binding')
    identifier(value['topic'])
    if topic is not None and value['topic'] != topic:
        raise ValueError('Template belongs to another topic')
    validate_definition(value['definition'])
    if not isinstance(value['source'], str) or not value['source'].strip():
        raise ValueError('Template source description required')
    if digest({k: v for k, v in value.items() if k != 'version'}) != value['version']:
        raise ValueError('Template changed after preview')
    return value


def validate_blocks(definition, content):
    if not isinstance(content, dict) or set(content) - {n['id'] for n in sections(definition)}:
        raise ValueError('Report content must map to confirmed template section IDs')
    for blocks in content.values():
        if not isinstance(blocks, list):
            raise ValueError('Section content must be a list of typed blocks')
        for b in blocks:
            if not isinstance(b, dict):
                raise ValueError('Invalid report block')
            if b.get('type') == 'paragraph':
                valid = set(b) == {'type', 'text'} and isinstance(b['text'], str)
            elif b.get('type') == 'list':
                valid = set(b) == {'type', 'items'} and isinstance(b['items'], list) and all(isinstance(x, str) for x in b['items'])
            elif b.get('type') == 'table':
                valid = (set(b) == {'type', 'columns', 'rows'} and isinstance(b['columns'], list) and bool(b['columns'])
                         and all(isinstance(x, str) for x in b['columns']) and isinstance(b['rows'], list)
                         and all(isinstance(r, list) and len(r) == len(b['columns']) and all(isinstance(x, (str, int, float)) and not isinstance(x, bool) for x in r) for r in b['rows']))
            else:
                valid = False
            if not valid:
                raise ValueError('Unsupported or malformed report block')


class Templates:
    def __init__(self, store):
        self.store = store

    def propose(self, topic, definition, source):
        identifier(topic)
        value = json.loads(canonical({'schema_version': 1, 'topic': topic, 'definition': definition, 'source': source}))
        value['version'] = digest(value)
        validate_binding(value, topic)
        return value

    def confirm(self, topic, proposal, approved, expected_version=None):
        value = json.loads(canonical(validate_binding(proposal, topic)))
        if approved != value['version']:
            raise ValueError('Explicit confirmation of the unchanged template version required')
        folder = self.store.root/'templates'/topic
        with lock(self.store.root):
            old = self.require(topic) if (folder/'head.json').exists() else None
            if (old['version'] if old else None) != expected_version:
                raise ValueError('Template selection changed; review the current selection first')
            write_json(folder/(value['version']+'.json'), value)
            write_json(folder/'head.json', {'version': value['version']})
        return value

    def get(self, topic, version):
        identifier(topic); identifier(version)
        value = read_json(self.store.root/'templates'/topic/(version+'.json'))
        if value['version'] != version:
            raise ValueError('Template history binding mismatch')
        return validate_binding(value, topic)

    def require(self, topic):
        identifier(topic)
        head = self.store.root/'templates'/topic/'head.json'
        if not head.exists():
            raise TemplateRequired(topic)
        return self.get(topic, read_json(head)['version'])
