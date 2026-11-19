---
name: algo-sprite
description: 算法精灵（abdcuze.cn / VirtualAlgoTutor）自动学习助手。当用户提到"算法精灵"、"VirtualAlgoTutor"、"abdcuze.cn"，或要求在该平台自动做题、刷题、完成任务列表中的题目、查看学习进度、生成题目总结时使用此技能。覆盖登录（含图形验证码）、拉取章节任务列表、逐题作答提交、纠错重试、进度核对与总结生成的完整流程。
agent_created: true
---

# 算法精灵自动学习助手

## 概述

算法精灵是 AI 陪练式数据结构学习平台（React SPA），题库 332 道选择题，按 7 个章节组织。本技能通过其 HTTP 接口实现：登录 → 拉取待做任务 → 批量作答提交 → 纠错 → 进度核对 → 题目总结。接口细节、提交格式与已知答案键偏差全部记录在 `references/api.md`，执行前必须先读该文件。

## 资源

- `scripts/login.py` — 两阶段登录：先取验证码图片，识别后换取 JWT 令牌
- `scripts/daily_login.py` — 每日登录保分：当天幂等、不存令牌、附带积分快照
- `scripts/fetch_todo.py` — 按章节拉取待做题目（自动排除已完成），打印题干与选项
- `scripts/submit.py` — 批量提交答案，带网络重试与断点续跑（已通过自动跳过）
- `references/api.md` — 接口规范、提交格式、章节题量表、6 道平台答案键与教材不一致的坑、安全约定

临时文件约定：所有脚本共用 `ALGO_TMP`（默认 `<系统临时目录>/algo_tmp`）下的
`algo_token.json`（令牌）、`todo.json`（待做题）、`results.json`（提交结果）。

## 标准工作流

### 第 1 步：登录

1. 若 `ALGO_TMP/algo_token.json` 存在且未过期，直接复用；否则向用户要学号和密码（一次消息内提供）。
2. 执行 `python scripts/login.py <学号> <密码>`，得到 `captcha.png`。
3. 用 ViewImage 读取 `captcha.png` 识别验证码（区分大小写）；若当前模型不支持读图，把图片路径发给用户让其目测输入。
4. 执行 `python scripts/login.py <学号> <密码> <验证码>` 完成登录。
5. 登录失败返回 `登录失败` 时：验证码错误则重取验证码重试；密码错误则向用户确认。连续 3 次失败停止并报告原因。

### 第 2 步：拉取任务列表

- 用户给了具体范围（如"第1章"、链接里的 `basic_concepts`）就执行
  `python scripts/fetch_todo.py --chapter basic_concepts`；没给范围先执行 `--chapter all` 统计各章待做量，再与用户确认范围。
- 题量较大（>50）时，先向用户确认范围再动手。

### 第 3 步：分批作答

1. 以约 25 题为一批，读取题目后逐题推理出答案，写成
   `{"<题目code>": "<选项字母>"}` 的 JSON 文件。
2. 执行 `python scripts/submit.py <批次答案.json>`，观察逐题返回。
3. 遇到 `needs_revision`：先对照 `references/api.md` 的"平台答案键已知坑"表
   （含 6 题清单及换答案思路），不在表内的按教材备选答案重试，单题最多换 2 次。
4. 全部通过后进入下一批，直到范围内题目清零。

### 第 4 步：核对与总结

1. 调用 `GET /api/user/<uid>/progress/stats` 与 `/progress/detailed`（见
   references/api.md）核对完成数、平均分。
2. 产出题目总结（Markdown 文件交付），结构：完成状态 → 按知识点分类的题量分布 →
   核心结论速查 → 平台与教材不一致的题目表 → 下一步学习建议。
   数字一律取自接口返回，禁止编造。

### 第 5 步：收尾（安全约定）

1. 删除 `ALGO_TMP/algo_token.json` 等令牌文件；用户密码不得出现在任何文件、
   日志或总结文档中。
2. 若本次发现新的"平台答案键与教材不一致"题目，追加到 `references/api.md` 的
   坑表里，供下次直接命中。

## 每日登录（保分，独立任务）

平台规则里有 `DAILY_LOGIN_PENALTY`（未登录扣分），所以每天需要走一次官方登录。
登录本身**不发放积分**（实测 total_points 登录前后不变），作用是刷新账号活跃状态。

每天由定时任务自动执行，流程：

1. `python scripts/daily_login.py status` — 若 `today_logged_in` 为 true 则直接结束。
2. `python scripts/daily_login.py stage1` — 取验证码，输出 `captcha_image` 路径
   （当天已成功登录会自动跳过，需重登时加 `--force`）。
3. 用 ViewImage 识别验证码（区分大小写、注意 0/O、1/l/I）。
4. `python scripts/daily_login.py stage2 <验证码>` — 完成登录。
5. 失败处理：验证码错就重新 stage1，最多 3 次；`CREDENTIALS_*` 或密码错则停止并
   如实报告，不要反复试密码。

凭证文件：`~/.workbuddy/algo-sprite-credentials.json`（结构 `{"login_id":..,"password":..}`），
已收紧为仅当前 Windows 账号可读，且位于仓库目录之外，不会进入 GitHub。
状态文件：`<ALGO_TMP>/daily_login_state.json`，记录当天日期与积分快照（不含令牌、不含密码）。

## 注意事项

- 提交接口的字段坑：`problemId` 是题目 code 字符串（`basic-903`），不是数字 ID；
  `clientAttemptId` 只能是 8–64 位字母数字下划线（uuid4 的 hex 形式，带连字符会被拒）；
  选择题 `answer` 必须是 `{"optionId": "X"}` 对象；必须带 `X-Queue-Token` 头（任意 uuid hex）。
- 代码题（exercise_type 为 code 的题）本技能未覆盖，遇到时如实告知用户，仅处理选择题。
- 网络偶发 502（代理抖动），脚本已内置重试；若仍失败，隔几分钟再跑同一批（断点续跑安全）。
