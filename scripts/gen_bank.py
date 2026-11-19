# -*- coding: utf-8 -*-
"""生成题库汇总 Markdown（全量题目 + 答案 + 坑题标注）。

用法:
  python gen_bank.py --out 题库汇总.md
  python gen_bank.py --scope all --out 全量题库.md
  python gen_bank.py --problems <题库json> --out 题库汇总.md

默认 scope=done：只输出「有作答记录」的章节（章内题目全列，未作答的标「未作答」）。
"""
import argparse
import collections
import datetime
import json
import os
import re

import report_data as rd


def opt_line(options, correct):
    parts = []
    for o in options or []:
        label = (o.get('label') or '').strip()
        mark = ' ✅' if o.get('id') == correct else ''
        parts.append(f"{o.get('id')} {label}{mark}")
    return ' ／ '.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='算法精灵_题库汇总.md')
    ap.add_argument('--problems', help='本地题库 json（不传则由脚本自动拉取/读缓存）')
    ap.add_argument('--scope', choices=['done', 'all'], default='done')
    args = ap.parse_args()

    token, uid = rd.load_token()
    problems = rd.load_problems(token, args.problems)
    answers = rd.load_answers()
    progress = rd.load_progress(token, uid)
    issues = rd.load_known_issues()
    prog = {r.get('problem_code'): r for r in progress}

    scope = rd.done_chapters(problems, answers, progress) if args.scope == 'done' \
        else {c for c, _ in rd.CHAPTERS}

    lines = [
        '# 算法精灵 题库汇总（复习用）', '',
        f'> 生成时间：{datetime.date.today().isoformat()}　数据来源：平台题库 + 本人作答记录',
        f'> 范围：{args.scope == "done" and "仅已作答章节" or "全部 7 章"}；'
        f'题库共 {len(problems)} 题，答案库已有 {len(answers)} 题', '',
        '**标记说明**：✅ 该选项为平台判定的正确答案；⚠ 平台答案与教材口径有分歧；'
        '❗ 平台错题（答案不在选项里）。', '', '---', '',
    ]

    total_shown = 0
    answered_shown = 0
    for code, name in rd.CHAPTERS:
        if code not in scope:
            continue
        pool = [p for p in problems if p.get('category_code') == code]
        if not pool:
            continue
        choice_n = sum(1 for p in pool if p.get('options'))
        code_n = len(pool) - choice_n
        lines.append(f'## {name}（{len(pool)} 题，选择 {choice_n} + 代码 {code_n}）')
        lines.append('')
        for p in pool:
            pid = p['problem_code']
            desc = (p.get('description') or p.get('quiz_question') or p.get('title') or '').strip()
            total_shown += 1
            ans = answers.get(pid)
            if ans:
                answered_shown += 1
            flag = ''
            if pid in issues:
                flag = ' ⚠' if ans else ' ❗'
            lines.append(f'**【{pid}】{desc}**{flag}')
            if p.get('options'):
                lines.append('　' + opt_line(p['options'], ans))
                if ans:
                    lines.append(f'　答案：**{ans}**')
                    if pid in issues:
                        lines.append(f'　⚠ 教材口径：{issues[pid]["textbook"]}（考试按教材写，按平台答）')
                else:
                    lines.append(f'　答案：{"❗ 平台错题，无正确选项" if pid in issues else "—（未作答）"}')
            else:
                hints = p.get('hints') or []
                lines.append(f'　[代码题] {"; ".join(hints[:2]) if hints else "见题目模板"}')
                r = prog.get(pid, {})
                if r:
                    lines.append(f'　平台记录：{"已完成" if r.get("completed") == 1 else "未完成"}，得分 {r.get("score")}')
                elif ans:
                    lines.append('　平台记录：已通过')
                else:
                    lines.append('　平台记录：未提交')
            lines.append('')
        lines.append('---')
        lines.append('')

    lines += ['## 平台答案与教材不一致的题目', '',
              '这些题从 Excel 导入时选项被拆错，判分按原始字母。复习按教材记、上机按平台答。',
              '', '| 题号 | 考点 | 平台判分 | 教材口径 |', '|---|---|---|---|']
    for pid, info in sorted(issues.items()):
        lines.append(f'| {pid} | {info["desc"]} | {info["platform"]} | {info["textbook"]} |')
    lines += ['', '---', '',
              f'共列出 **{total_shown}** 题，其中已作答 **{answered_shown}** 题。',
              f'题库接口本身不含正确答案字段，所有答案来自 `~/.workbuddy/algo-sprite-answers.json`',
              '（由 submit.py 每次提交成功自动累积）。', '']

    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf-8').write('\n'.join(lines))
    print(json.dumps({'ok': True, 'out': out, 'chapters': len(scope),
                      'problems_shown': total_shown, 'answered': answered_shown},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
