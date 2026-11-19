# -*- coding: utf-8 -*-
"""报告生成公共数据层：题库、答案库、进度、坑题清单。

被 gen_bank.py 与 gen_summary.py 共用。坑题清单直接解析 references/api.md，
保证只有一处需要维护。
"""
import os
import re
import json
import tempfile
import urllib.request

BASE = 'https://abdcuze.cn'
TMP = os.environ.get('ALGO_TMP') or os.path.join(tempfile.gettempdir(), 'algo_tmp')
HOME = os.path.expanduser('~')
ANSWERS = os.environ.get('ALGO_ANSWERS') or os.path.join(
    HOME, '.workbuddy', 'algo-sprite-answers.json')
PROBLEMS_CACHE = os.environ.get('ALGO_PROBLEMS') or os.path.join(
    HOME, '.workbuddy', 'algo-sprite-problems.json')
LEGACY_CACHES = [
    os.path.join(TMP, 'problems.json'),
    os.path.join(tempfile.gettempdir(), 'problems.json'),
]
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_MD = os.path.join(SKILL_DIR, 'references', 'api.md')

CHAPTERS = [
    ('BASIC_CONCEPTS', '第1章 数据结构与算法基本概念'),
    ('LINEAR_LIST', '第2章 线性表'),
    ('STACK_QUEUE', '第3章 栈和队列'),
    ('TREE_BINARY', '第4章 树与二叉树'),
    ('GRAPH', '第5章 图'),
    ('SEARCH', '第6章 查找'),
    ('SORTING', '第7章 排序'),
]
CHAPTER_NAME = dict(CHAPTERS)


def load_token():
    """读刷题流程留下的令牌；没有就返回 (None, None)，走本地缓存降级。"""
    p = os.path.join(TMP, 'algo_token.json')
    try:
        d = json.load(open(p, encoding='utf-8'))
        return d.get('token'), d.get('user_id')
    except (OSError, ValueError):
        return None, None


def api_get(path, token):
    req = urllib.request.Request(BASE + path)
    req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {'__error__': str(e)}


def load_answers():
    try:
        return json.load(open(ANSWERS, encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_answers(db):
    os.makedirs(os.path.dirname(ANSWERS), exist_ok=True)
    tmp = ANSWERS + '.tmp'
    json.dump(db, open(tmp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.replace(tmp, ANSWERS)


def load_problems(token=None, path=None):
    """优先指定文件 → 带令牌拉接口并缓存 → 持久缓存 → 旧临时缓存。"""
    if path and os.path.isfile(path):
        return json.load(open(path, encoding='utf-8'))
    if token:
        d = api_get('/api/problems', token)
        if isinstance(d, list) and d:
            os.makedirs(os.path.dirname(PROBLEMS_CACHE), exist_ok=True)
            json.dump(d, open(PROBLEMS_CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
            return d
    for cache in [PROBLEMS_CACHE] + LEGACY_CACHES:
        if os.path.isfile(cache):
            d = json.load(open(cache, encoding='utf-8'))
            if cache != PROBLEMS_CACHE:
                os.makedirs(os.path.dirname(PROBLEMS_CACHE), exist_ok=True)
                json.dump(d, open(PROBLEMS_CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
            return d
    raise SystemExit('拿不到题库：加 --problems <题库json>，或先登录让脚本自动拉取')


def load_progress(token, uid):
    if not token or not uid:
        return []
    d = api_get('/api/user/%s/progress/detailed' % uid, token)
    return d if isinstance(d, list) else []


def load_stats(token, uid):
    if not token or not uid:
        return {}
    d = api_get('/api/user/%s/progress/stats' % uid, token)
    return d if isinstance(d, dict) and '__error__' not in d else {}


def load_known_issues():
    """从 references/api.md 的坑题表解析 {code: {desc, platform, textbook}}。"""
    issues = {}
    try:
        text = open(API_MD, encoding='utf-8').read()
    except OSError:
        return issues
    pat = re.compile(r'^\|\s*([a-z]+-\d+)\s+([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|')
    for line in text.splitlines():
        m = pat.match(line)
        if m:
            code, desc, platform, textbook = m.groups()
            issues[code] = {'desc': desc.strip(), 'platform': platform.strip(),
                            'textbook': textbook.strip()}
    return issues


def classify(desc):
    """按题干关键词粗分知识点，用于总结里的题量分布。"""
    rules = [
        ('时间复杂度与算法分析', r'时间复杂度|频度|语句|算法分析|计算量|空间复杂度'),
        ('文件与外部排序', r'文件|归并段|VSAM|缓冲池|磁带|散列文件|ISAM'),
        ('字符串', r'串|子串|模式匹配|next'),
        ('数组与矩阵', r'矩阵|数组|压缩存储'),
        ('图', r'图|顶点|路径|拓扑|生成树|Prim|Floyd|邻接|关键路径|最短路径'),
        ('树与堆', r'树|堆|结点|二叉|哈夫曼|线索|森林|平衡'),
        ('线性表与链表', r'链表|线性表|顺序表|指针|循环'),
        ('栈、队列与递归', r'栈|队列|递归|出栈|入栈'),
        ('排序', r'排序|冒泡|快速|归并|堆排|希尔'),
        ('查找', r'查找|哈希|散列|二叉排序树|ASL|折半'),
    ]
    for name, pattern in rules:
        if re.search(pattern, desc):
            return name
    return '概念与术语'


def done_chapters(problems, answers, progress):
    """返回「有作答记录」的章节 code 集合，用于只整理已做章节。"""
    by_code = {p['problem_code']: p for p in problems}
    chapters = set()
    for code in answers:
        p = by_code.get(code)
        if p:
            chapters.add(p.get('category_code'))
    for r in progress:
        code = r.get('problem_code')
        p = by_code.get(code)
        if p and (r.get('completed') == 1 or (r.get('score') or 0) > 0):
            chapters.add(p.get('category_code'))
    return chapters
