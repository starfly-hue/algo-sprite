# -*- coding: utf-8 -*-
"""生成题目总结的数据骨架（完成情况、知识点分布、坑题表、分章题号索引）。

公式口诀需要理解题意，由技能流程里的 AI 基于「四、分章题目索引」补写，
插入位置是文件末尾的 <!-- AI_EXPLANATION --> 标记。

用法:
  python gen_summary.py --out 算法精灵_题目总结.md
  python gen_summary.py --problems <题库json> --scope all
"""
import argparse
import collections
import datetime
import json
import os

import report_data as rd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='算法精灵_题目总结.md')
    ap.add_argument('--problems', help='本地题库 json')
    ap.add_argument('--scope', choices=['done', 'all'], default='done')
    ap.add_argument('--explanations', help='AI 写好的考点速查 Markdown，嵌到文档末尾')
    args = ap.parse_args()

    token, uid = rd.load_token()
    problems = rd.load_problems(token, args.problems)
    answers = rd.load_answers()
    progress = rd.load_progress(token, uid)
    stats = rd.load_stats(token, uid)
    issues = rd.load_known_issues()
    prog = {r.get('problem_code'): r for r in progress}

    scope = rd.done_chapters(problems, answers, progress) if args.scope == 'done' \
        else {c for c, _ in rd.CHAPTERS}

    L = [
        '# 算法精灵 题目总结（期中复习用）', '',
        f'> 生成时间：{datetime.date.today().isoformat()}　范围：'
        f'{args.scope == "done" and "仅已作答章节" or "全部 7 章"}',
        '> 数字来源：平台进度接口 + 本地答案库；题库接口不含正确答案字段。', '',
        '---', '', '## 一、完成情况', '',
    ]

    if stats:
        L.append(f'平台实时统计：**已作答 {stats.get("total_problems_attempted", "待核")} 题，'
                 f'完成 {stats.get("total_problems_completed", "待核")} 题，'
                 f'平均分 {stats.get("average_score", "待核")}**。')
    else:
        L.append(f'平台实时统计：**待核**（当前无有效登录令牌）。'
                 f'本地答案库已累积 **{len(answers)}** 题，下表「已作答」按答案库统计。')
    L += ['', '| 章节 | 题库题数 | 已作答 | 选择题 | 代码题 |', '|---|---|---|---|---|']
    for code, name in rd.CHAPTERS:
        if code not in scope:
            continue
        pool = [p for p in problems if p.get('category_code') == code]
        done = sum(1 for p in pool
                   if p['problem_code'] in answers
                   or prog.get(p['problem_code'], {}).get('completed') == 1)
        choice_n = sum(1 for p in pool if p.get('options'))
        L.append(f'| {name} | {len(pool)} | {done} | {choice_n} | {len(pool) - choice_n} |')
    L += ['', '---', '', '## 二、按知识点分类的题量分布', '',
          '（按题干关键词粗分，同一题只归一类，用于判断复习重心）', '',
          '| 知识点 | 题量 | 占比 |', '|---|---|---|']
    shown = [p for p in problems if p.get('category_code') in scope]
    counter = collections.Counter(
        rd.classify((p.get('description') or p.get('quiz_question') or p.get('title') or ''))
        for p in shown)
    for name, n in counter.most_common():
        L.append(f'| {name} | {n} | {n * 100 // max(len(shown), 1)}% |')
    L += ['', '---', '', '## 三、平台答案与教材不一致的题目', '',
          '这些题按教材选会被判错，复习按教材记、上机按平台答。', '',
          '| 题号 | 考点 | 平台判分 | 教材口径 |', '|---|---|---|---|']
    for pid, info in sorted(issues.items()):
        L.append(f'| {pid} | {info["desc"]} | {info["platform"]} | {info["textbook"]} |')
    L += ['', '---', '', '## 四、分章题目索引（供归纳考点）', '',
          '格式：`题号 题干 → 答案`。代码题以 CODE 标记。', '']
    for code, name in rd.CHAPTERS:
        if code not in scope:
            continue
        pool = [p for p in problems if p.get('category_code') == code]
        L.append(f'### {name}（{len(pool)} 题）')
        L.append('')
        for p in pool:
            pid = p['problem_code']
            desc = (p.get('description') or p.get('quiz_question') or p.get('title') or '').strip()
            desc = ' '.join(desc.split())[:90]
            ans = answers.get(pid, ('CODE' if prog.get(pid, {}).get('completed') == 1 else '—'))
            L.append(f'- `{pid}` {desc} → **{ans}**')
        L.append('')
    L += ['---', '']
    if args.explanations and os.path.isfile(args.explanations):
        L.append('## 五、考点速查（必背公式与易错点）')
        L.append('')
        L.append(open(args.explanations, encoding='utf-8').read().strip())
        L.append('')
    else:
        L += ['<!-- AI_EXPLANATION -->',
              '（此处由 AI 补写「考点速查」：按章列出必背公式、易错点与对应题号，'
              '并用 --explanations 重新生成以删掉本标记。数字必须来自上文，不得编造。）', '']

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write('\n'.join(L))
    print(json.dumps({'ok': True, 'out': out, 'chapters': len(scope),
                      'indexed': len(shown), 'stats_available': bool(stats)},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
