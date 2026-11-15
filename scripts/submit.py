# -*- coding: utf-8 -*-
"""提交答案（带网络重试与断点续跑）
用法: python submit.py <answers.json> [results.json]
answers.json 格式: {"basic-903": "B", ...}
results.json 默认 TMP/results.json，已 passed 的题自动跳过
"""
import sys, json, os, time, uuid, urllib.request, urllib.error, random, tempfile

BASE = 'https://abdcuze.cn/api/attempts'
TMP = os.environ.get('ALGO_TMP', os.path.join(tempfile.gettempdir(), "algo_tmp"))


def submit(token, code, opt):
    body = {
        "clientAttemptId": uuid.uuid4().hex,   # 必须 8-64 位字母数字下划线，不能带连字符
        "problemId": code,                     # 注意是题目 code 字符串（如 basic-903），不是数字ID
        "answer": {"optionId": opt},           # 选择题必须是对象，字段名是 optionId
        "timeSpentSeconds": random.randint(50, 160),
    }
    data = json.dumps(body).encode()
    for attempt in range(5):
        try:
            req = urllib.request.Request(BASE, data=data, method='POST')
            req.add_header('Authorization', 'Bearer ' + token)
            req.add_header('Content-Type', 'application/json')
            req.add_header('X-Queue-Token', uuid.uuid4().hex)   # 必带，值任意 uuid hex
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode())
            except Exception:
                return {"error": f"HTTP {e.code}"}
        except Exception as e:
            time.sleep(2 + attempt * 2)
    return {"error": "network"}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    plan = json.load(open(sys.argv[1], encoding='utf-8'))
    outpath = sys.argv[2] if len(sys.argv) > 2 else os.path.join(TMP, 'results.json')
    auth = json.load(open(os.path.join(TMP, 'algo_token.json'), encoding='utf-8'))
    token = auth['token']
    results = json.load(open(outpath, encoding='utf-8')) if os.path.exists(outpath) else {}
    for code, opt in plan.items():
        if code in results and results[code].get('status') == 'passed':
            print(f'{code} 跳过(已完成)')
            continue
        res = submit(token, code, opt)
        results[code] = {"opt": opt, **res}
        print(f'{code} -> {opt} | {res.get("status", res.get("error"))} | score={res.get("score")}')
        json.dump(results, open(outpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        time.sleep(0.8)
    ok = sum(1 for v in results.values() if v.get('status') == 'passed')
    print(f'\n合计 {len(results)} 条，通过 {ok} 条')


if __name__ == '__main__':
    main()
