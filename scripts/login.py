# -*- coding: utf-8 -*-
"""算法精灵登录：两阶段使用
阶段1（取验证码）: python login.py <loginId> <password>
   -> 保存 captcha.json + captcha.png，打印提示后退出
   -> 用 ViewImage 读 captcha.png 得到验证码字符（区分大小写）
阶段2（登录）:    python login.py <loginId> <password> <captchaAnswer>
   -> POST /api/auth/login，成功则把 token 和 user_id 写入 algo_token.json
"""
import sys, json, uuid, base64, urllib.request, urllib.error, os, time, tempfile

BASE = 'https://abdcuze.cn/api'
TMP = os.environ.get('ALGO_TMP', os.path.join(tempfile.gettempdir(), "algo_tmp"))
os.makedirs(TMP, exist_ok=True)


def post(url, payload, token=None, queue=False):
    data = json.dumps(payload).encode()
    for i in range(4):
        try:
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header('Content-Type', 'application/json')
            if token:
                req.add_header('Authorization', 'Bearer ' + token)
            if queue:
                req.add_header('X-Queue-Token', uuid.uuid4().hex)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read().decode())
            except Exception:
                return {"error": f"HTTP {e.code}"}
        except Exception as e:
            print(f'  网络重试 {i+1}: {e}')
            time.sleep(2 + i * 2)
    return {"error": "network"}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    login_id, password = sys.argv[1], sys.argv[2]

    if len(sys.argv) >= 4:
        cap = json.load(open(os.path.join(TMP, 'captcha.json'), encoding='utf-8'))
        res = post(f'{BASE}/auth/login', {
            "loginId": login_id, "password": password,
            "captchaToken": cap['token'], "captchaAnswer": sys.argv[3],
        })
        if res.get('success') and res.get('token'):
            info = {"token": res['token'], "user_id": res['user']['user_id'],
                    "username": res['user'].get('username')}
            json.dump(info, open(os.path.join(TMP, 'algo_token.json'), 'w', encoding='utf-8'),
                      ensure_ascii=False)
            print('登录成功 user_id=', info['user_id'])
        else:
            print('登录失败:', json.dumps(res, ensure_ascii=False)[:300])
        return

    # 阶段1: 取验证码
    for i in range(4):
        try:
            with urllib.request.urlopen(f'{BASE}/auth/captcha?loginId={login_id}', timeout=30) as r:
                d = json.loads(r.read().decode())
            img = d['image'].split(',', 1)[1]
            open(os.path.join(TMP, 'captcha.png'), 'wb').write(base64.b64decode(img))
            json.dump({"token": d['token']}, open(os.path.join(TMP, 'captcha.json'), 'w'))
            print('验证码已保存:', os.path.join(TMP, 'captcha.png'))
            print('下一步: 用 ViewImage 识别后执行 python login.py <loginId> <password> <验证码>')
            return
        except Exception as e:
            print(f'  网络重试 {i+1}: {e}')
            time.sleep(2 + i * 2)
    print('获取验证码失败')


if __name__ == '__main__':
    main()
