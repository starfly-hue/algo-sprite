# 算法精灵（abdcuze.cn）接口参考

站点为 React SPA，所有数据走 `/api/*`，除登录/验证码外均需请求头
`Authorization: Bearer <JWT>`。

## 核心接口

| 用途 | 方法与路径 | 说明 |
|---|---|---|
| 图形验证码 | `GET /api/auth/captcha?loginId=<学号>` | 返回 `{token, image}`，image 是 data:image/png;base64 |
| 登录 | `POST /api/auth/login` | body `{loginId, password, captchaToken, captchaAnswer}`；成功返回 `{success, token, user:{user_id,...}}` |
| 题库全量 | `GET /api/problems` | 332 题（2026-11 快照），含题干、选项、hints |
| 单题详情 | `GET /api/problems/<code>` | code 如 `basic-903` |
| 提交答案 | `POST /api/attempts` | 见下方"提交格式" |
| 进度明细 | `GET /api/user/<uid>/progress/detailed` | 每题 completed/score/best_score |
| 进度统计 | `GET /api/user/<uid>/progress/stats` | 总完成数、平均分、时长 |
| 推荐/薄弱点 | `GET /api/user/<uid>/recommendations` | todayGoal、weakTopics、suggestedProblems |
| 积分快照 | `GET /api/user/<uid>/points` | total_points、study_points、last_activity、last_login_reward_ms |
| 每日统计 | `GET /api/user/<uid>/daily-stats?days=N` | 逐日 total_time_minutes、streak_days |

## 提交格式（最容易踩的坑）

```json
POST /api/attempts
{
  "clientAttemptId": "32位hex（uuid4().hex，不能带连字符）",
  "problemId": "basic-903",        // 字符串题目code，不是 problem_id 数字！
  "answer": {"optionId": "B"},      // 选择题必须是对象，字段名 optionId
  "timeSpentSeconds": 95
}
```
- 请求头必须带 `X-Queue-Token: <任意uuid hex>`，值无需注册
- 正确：`{"status":"passed","score":100,...}`
- 错误：`{"status":"needs_revision","score":0,"feedback":["回答错误，请复习后再试。"]}`
  ——错误响应不会告知正确答案，只能换选项重试

## 章节与题量（category_code）

| code | 章节 | 题量 | 题型 |
|---|---|---|---|
| basic_concepts | 第1章 基本概念 | 149 | 全部单选 |
| linear_list | 第2章 线性表 | 5 | 单选+代码 |
| stack_queue | 第3章 栈和队列 | 17 | 单选+代码 |
| tree_binary | 第4章 树与二叉树 | 56 | 单选 |
| graph | 第5章 图 | 7 | 单选 |
| search | 第6章 查找 | 31 | 单选 |
| sorting | 第7章 排序 | 67 | 单选+代码 |

## 代码题提交格式

代码题（exercise_type 为 code，或无 exercise_type 但有 code_template）同样走
`POST /api/attempts`，answer 换成：

```json
{
  "clientAttemptId": "32位hex",
  "problemId": "linear-1",
  "answer": {"type": "code", "language": "typescript", "source": "完整代码", "pasteDetected": false},
  "timeSpentSeconds": 240
}
```
- 服务端会调 LLM 做四维评分（correctness / efficiency / style / edgeCases），返回 `status: passed` 与 `score`
- 分数通常 85–100，passed 即可
- 语言用 `typescript` 或 `cpp`（题面模板是 C++ 就用 cpp）

### 代码题的两个约束

1. **频率限制**：连续提交会被拒，返回
   `{"error":"操作太频繁啦...","code":"RATE_LIMIT"}`。实测短时间约能过 3 题，
   之后需等几分钟再试。遇到就等 60–90 秒重试，不要改答案硬刷。
2. **前置任务**：部分题有前置依赖，返回
   `{"error":"请先完成前置任务：stack-1","code":"PREREQUISITE_INCOMPLETE","prerequisiteIds":["stack-1"]}`。
   已知链：`queue-1` 依赖 `stack-1`，`tree-2` 依赖 `tree-1`。先做前置再回头补。

## 平台答案键的已知坑（与教材口径不一致）

题目从 Excel 批量导入，部分选项被拆错（如 basic-162 的选项变成
"A / 索引集 / 顺序集 / 数据集 / 文件集"），判分按原始字母顺序。以下 6 题按教材选
会被判错，须按平台口径作答：

| 题号 | 平台判分 | 教材口径 |
|---|---|---|
| basic-162 VSAM三部分中不正确的 | D 数据集 | 文件集 |
| basic-788 一个算法应该是 | B 问题求解步骤的描述 | 要满足五个基本特性 |
| basic-816 串值描述正确的是 | C 必须用一对单引号括起来 | 字符序列可直接赋值 |
| basic-829 有向图邻接表顶点v出现次数 | B 出度 | 入度 |
| basic-860 最适于表示稀疏无向图 | E 邻接表 | 邻接多重表 |
| basic-896 邻接表存储时Prim复杂度 | C O(n²) | O(n+e) |
| tree-63 完全二叉树1001结点叶子数 | 无解（501不在选项里，五个选项全判错） | 501 |
| tree-79 哈夫曼结点总数（选项被拆成5项） | D（对应"2n+1"位置，实为2n-1） | 2n-1 |
| tree-82 平衡调整（右孩子BF=1） | C RL | RR |

遇到 `needs_revision` 时：优先怀疑题目属于上述"导入错乱"类型，按
"原字母顺序"逻辑换选项重试；其余题目换备选答案。选项被拆坏（出现
"A / 索引集 B / 顺序集 C" 这种）的题，答案字母往往仍按原始顺序，先试原字母。

**注意**：`tree-63` 这类题无解，试遍所有选项后应放弃并在总结里标注为平台错题，
不要无限重试。

## 每日登录与积分（实测记录）

- 平台前端存在积分变动类型枚举 `DAILY_LOGIN_PENALTY: "未登录扣分"`，即长时间不登录
  会扣积分；扣分阈值与每次扣多少：**待核**（前端无展示逻辑，无流水接口可查）。
- 实测 2026-11-19：登录前后 `total_points` 均为 1888.00、`study_points` 均为 1971.00，
  **登录不发放积分奖励**，也不产生积分变动。
- 登录会更新 `/api/user/<uid>/profile` 的 `last_login` 与 points 表的 `last_activity`
  / `updated_at`；因此"每天登录"的作用是维持账号活跃，规避未登录扣分。
- 是否真的能免扣，**没有接口可直接验证**，只能通过每日 `daily_login.py` 记录的积分
  快照长期对比（`points_delta_since_last_login` 为负说明被扣了）。
- `last_login_reward_ms` 为毫秒时间戳（示例 1795059055911 → 2026-11-19 11:30:55），
  多次登录不变，含义待核。

## 安全约定

- 用户密码只用于登录请求，不得写入任何日志、总结文档、提交信息或对话输出
- 登录令牌（algo_token.json）用完任务后删除；临时文件目录 TMP 默认为系统临时目录下 `algo_tmp`
- **唯一例外**：每日自动登录需要无人值守，密码存放于仓库外的
  `~/.workbuddy/algo-sprite-credentials.json`，权限已收紧为仅当前 Windows 账号可读，
  并已在 `.gitignore` 中排除凭证类文件名，确保不会进入公开仓库
- `daily_login.py` 完成后不留令牌（登录行为本身即目的），只写不含敏感信息的
  `daily_login_state.json`
