#!/usr/bin/env python3
"""算法精灵每日登录（保住积分不被"未登录扣分"扣掉）。

两阶段设计：验证码需要 AI 识图，脚本只负责取图与提交。

用法：
  python daily_login.py status              查看今天是否已经登录过（含上次积分快照）
  python daily_login.py stage1              取验证码，输出图片路径（当天已登录会跳过）
  python daily_login.py stage1 --force      强制重新取验证码
  python daily_login.py stage2 <验证码>     带验证码完成登录，并记录积分快照

凭证默认读取 ~/.workbuddy/algo-sprite-credentials.json，
可用环境变量 ALGO_CREDENTIALS 覆盖路径；临时目录可用 ALGO_TMP 覆盖。
登录成功后不保存令牌（登录行为本身即目的），只记录当天成功状态。
"""
import sys
import os
import json
import base64
import datetime
import tempfile
import urllib.parse
import urllib.request
import urllib.error

BASE = 'https://abdcuze.cn'
TMP = os.environ.get('ALGO_TMP') or os.path.join(tempfile.gettempdir(), 'algo_tmp')
CRED = os.environ.get('ALGO_CREDENTIALS') or os.path.join(
    os.path.expanduser('~'), '.workbuddy', 'algo-sprite-credentials.json')
STATE = os.path.join(TMP, 'daily_login_state.json')
CAPTCHA_PNG = os.path.join(TMP, 'daily_captcha.png')
CAPTCHA_META = os.path.join(TMP, 'daily_captcha.json')


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(code)


def today():
    return datetime.date.today().isoformat()


def load_credentials():
    if not os.path.isfile(CRED):
        out({'ok': False, 'error': 'CREDENTIALS_MISSING', 'path': CRED}, 1)
    try:
        with open(CRED, encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        out({'ok': False, 'error': 'CREDENTIALS_INVALID', 'detail': str(e)}, 1)
    login_id, password = d.get('login_id'), d.get('password')
    if not login_id or not password:
        out({'ok': False, 'error': 'CREDENTIALS_INCOMPLETE'}, 1)
    return str(login_id), str(password)


def request(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {'error': 'HTTP_%s' % e.code}
    except Exception as e:
        return {'error': 'NETWORK', 'detail': str(e)}


def fetch_points(token, uid):
    """用内存里的令牌查积分快照（令牌不落盘）。查不到返回 None。"""
    d = request('GET', '/api/user/%s/points' % uid, token=token)
    if not isinstance(d, dict) or 'total_points' not in d:
        return None
    try:
        return {
            'total_points': float(d['total_points']),
            'study_points': float(d['study_points']) if d.get('study_points') is not None else None,
            'server_last_activity': d.get('last_activity'),
        }
    except (TypeError, ValueError):
        return None


def read_state():
    try:
        with open(STATE, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def cmd_status():
    s = read_state()
    out({'ok': True, 'today': today(),
         'today_logged_in': s.get('last_success_date') == today(),
         'last_success_date': s.get('last_success_date'),
         'last_points': s.get('points_snapshot')})


def cmd_stage1(login_id, force=False):
    s = read_state()
    if not force and s.get('last_success_date') == today():
        out({'ok': True, 'already_logged_in': True, 'date': today(),
             'hint': '今天已经登录成功过，跳过；要强制重登加 --force'})
    d = request('GET', '/api/auth/captcha?loginId=' + urllib.parse.quote(login_id))
    token, image = d.get('token'), d.get('image')
    if not token or not image:
        out({'ok': False, 'error': 'CAPTCHA_FETCH_FAILED',
             'detail': str(d)[:200]}, 1)
    try:
        with open(CAPTCHA_PNG, 'wb') as f:
            f.write(base64.b64decode(image.split(',', 1)[-1]))
        with open(CAPTCHA_META, 'w', encoding='utf-8') as f:
            json.dump({'token': token}, f)
    except Exception as e:
        out({'ok': False, 'error': 'CAPTCHA_SAVE_FAILED', 'detail': str(e)}, 1)
    out({'ok': True, 'stage': 1, 'captcha_image': CAPTCHA_PNG,
         'hint': '用 ViewImage 读取该图片识别验证码，再执行 stage2 <验证码>'})


def cmd_stage2(login_id, password, answer):
    answer = (answer or '').strip()
    if not answer:
        out({'ok': False, 'error': 'EMPTY_CAPTCHA'}, 1)
    try:
        with open(CAPTCHA_META, encoding='utf-8') as f:
            meta = json.load(f)
    except (OSError, ValueError):
        out({'ok': False, 'error': 'CAPTCHA_EXPIRED',
             'hint': '重新执行 stage1 取一张新验证码'}, 1)
    d = request('POST', '/api/auth/login', {
        'loginId': login_id,
        'password': password,
        'captchaToken': meta['token'],
        'captchaAnswer': answer,
    })
    if not d.get('success'):
        out({'ok': False, 'error': 'LOGIN_FAILED',
             'detail': str(d.get('message') or d.get('error') or d)[:200],
             'hint': '验证码错就重新 stage1；密码错请更新凭证文件'}, 1)

    s = read_state()
    prev = s.get('points_snapshot') or {}
    uid = d.get('user', {}).get('user_id')
    pts = fetch_points(d.get('token'), uid) if uid else None
    delta = None
    if pts and prev.get('total_points') is not None:
        delta = round(pts['total_points'] - prev['total_points'], 2)

    s['last_success_date'] = today()
    s['last_login_at'] = datetime.datetime.now().isoformat(timespec='seconds')
    s['user_id'] = uid
    if pts:
        s['points_snapshot'] = pts
    with open(STATE, 'w', encoding='utf-8') as f:
        json.dump(s, f, ensure_ascii=False)
    for p in (CAPTCHA_META, CAPTCHA_PNG):
        try:
            os.remove(p)
        except OSError:
            pass
    out({'ok': True, 'stage': 2, 'logged_in': True, 'date': today(),
         'user_id': uid,
         'login_id_masked': login_id[:3] + '***',
         'points': pts,
         'points_delta_since_last_login': delta})


def main():
    os.makedirs(TMP, exist_ok=True)
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return
    cmd = args[0]
    if cmd == 'status':
        return cmd_status()
    login_id, password = load_credentials()
    if cmd == 'stage1':
        return cmd_stage1(login_id, force='--force' in args[1:])
    if cmd == 'stage2':
        rest = [a for a in args[1:] if not a.startswith('--')]
        return cmd_stage2(login_id, password, rest[0] if rest else '')
    print(__doc__)


if __name__ == '__main__':
    main()
