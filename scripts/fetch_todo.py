# -*- coding: utf-8 -*-
"""拉取待做题目与进度
用法: python fetch_todo.py [--chapter basic_concepts|linear_list|...|all]
输出: TMP/todo.json（待做题数组）并在控制台打印每题题干+选项
"""
import sys, json, os, urllib.request, tempfile

BASE = 'https://abdcuze.cn/api'
TMP = os.environ.get('ALGO_TMP', os.path.join(tempfile.gettempdir(), "algo_tmp"))

CHAPTERS = ["basic_concepts", "linear_list", "stack_queue",
            "tree_binary", "graph", "search", "sorting"]


def get(url, token):
    for i in range(4):
        try:
            req = urllib.request.Request(url)
            req.add_header('Authorization', 'Bearer ' + token)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception:
            import time
            time.sleep(2 + i * 2)
    raise RuntimeError('network: ' + url)


def main():
    chapter = 'all'
    if '--chapter' in sys.argv:
        chapter = sys.argv[sys.argv.index('--chapter') + 1]

    try:
        auth = json.load(open(os.path.join(TMP, 'algo_token.json'), encoding='utf-8'))
    except FileNotFoundError:
        print(f'未找到令牌文件 {os.path.join(TMP, "algo_token.json")}，请先运行 login.py 完成登录')
        return
    token, uid = auth['token'], auth['user_id']

    problems = get(f'{BASE}/problems', token)
    problems = [p for p in problems if p.get('is_active') == 1]
    try:
        progress = get(f'{BASE}/user/{uid}/progress/detailed', token)
    except Exception:
        progress = []
    done = {r['problem_code'] for r in progress if r.get('completed') == 1}

    pool = problems if chapter == 'all' else [
        p for p in problems if str(p.get('category_code', '')).lower() == chapter.lower()]
    todo = [p for p in pool if p['problem_code'] not in done]
    json.dump(todo, open(os.path.join(TMP, 'todo.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(progress, open(os.path.join(TMP, 'progress.json'), 'w', encoding='utf-8'), ensure_ascii=False)

    print(f'范围: {chapter} | 总题数 {len(pool)} | 已完成 {sum(1 for p in pool if p["problem_code"] in done)} | 待做 {len(todo)}')
    print(f'已写入 {os.path.join(TMP, "todo.json")}，打印全部待做题:')
    for p in todo:
        opts = ' / '.join(f"{o['id']}:{o['label'].strip()}" for o in (p.get('options') or []))
        print(f"[{p['problem_code']}] ({p.get('exercise_type')}) {p['description'].strip()}")
        if opts:
            print(f"   {opts}")


if __name__ == '__main__':
    main()
