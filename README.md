# algo-sprite

[算法精灵](https://abdcuze.cn)（VirtualAlgoTutor）自动学习助手。这是一个 **WorkBuddy（CodeBuddy）技能**，装好后一句话即可让 AI 帮你把平台的学习任务列表自动做完，并生成可用于复习的题目总结。这是数据结构篇。


> 平台本身是 AI 陪练式数据结构学习网站，题库 332 题、7 个章节。本技能直接对接其官方 HTTP 接口，模拟正常学习流程作答，不碰任何越权操作。

## 它能做什么

| 能力 | 说明 |
|---|---|
| 自动登录 | 学号 + 密码两阶段登录，图形验证码自动识别 |
| 拉取任务 | 按章节拉取待做题目，自动跳过已完成的 |
| 批量作答 | 选择题 + 代码题（AI 四维评分）分批提交，带断点续跑 |
| 纠错重试 | 答错自动换选项重试；内置平台错题清单直接命中 |
| 进度核对 | 完成数、平均分、薄弱点，全部取自平台接口真实数据 |
| 题目总结 | 生成 Markdown 复习资料：按知识点分类 + 全量题库汇总 |
| 每日登录保分 | 平台有"未登录扣分"规则，每天自动登录一次维持活跃，并记录积分快照 |
| 复习资料自动生成 | 刷完题自动产出「题库汇总」（全量题目+答案）与「题目总结」（考点+公式+题号索引） |

## 实测战绩

- 第 1–4 章 227 题完成 226 题，平均分 99（唯一未通过的是 `tree-63`，平台错题，正确答案不在选项里）
- 9 道代码题全部通过（88–95 分）：顺序表插入、链表反转、约瑟夫环、顺序栈、括号匹配、循环队列、二叉树遍历、哈夫曼编码、二叉树同构判断

## 安装

```bash
git clone git@github.com:starfly-hue/algo-sprite.git ~/.workbuddy/skills/algo-sprite
```

克隆到用户级技能目录后，新开对话即可生效（无需重启 WorkBuddy）。

## 使用

装好后直接对话触发，例如：

> 用算法精灵把第 7 章排序做完，给我题目总结

流程全自动：登录（首次需要你提供一次学号密码）→ 拉题 → 分批作答 → 纠错 → 核对进度 → 生成总结文档。题量超过 50 时会先和你确认范围。

## 每日自动登录（保分）

平台有"未登录扣分"规则（前端枚举 `DAILY_LOGIN_PENALTY`），所以每天需要登录一次。配置两步：

1. 建凭证文件 `~/.workbuddy/algo-sprite-credentials.json`：

```json
{ "login_id": "你的学号", "password": "你的密码" }
```

2. 建一个每天固定时间执行的定时任务（WorkBuddy 自动化），让它依次执行：

```bash
python ~/.workbuddy/skills/algo-sprite/scripts/daily_login.py status    # 今天已登录就结束
python ~/.workbuddy/skills/algo-sprite/scripts/daily_login.py stage1    # 取验证码
# 用 ViewImage 识别 captcha_image，再执行：
python ~/.workbuddy/skills/algo-sprite/scripts/daily_login.py stage2 <验证码>
```

脚本特性：当天已登录自动跳过（`--force` 可强制重登）、不保存登录令牌、失败时输出机器可读的 JSON、每次登录记录积分快照（`points_delta_since_last_login` 为负数说明被扣分了）。

> 注意：实测**登录本身不发积分**，也不产生积分变动，作用是刷新账号活跃状态。"每天登录能否完全免除未登录扣分"没有接口可以直接验证，只能靠积分快照长期观察。

## 复习资料生成

**默认行为**：每次刷完题会自动产出两份 Markdown，不用另外说。

也可以单独跑：

```bash
python ~/.workbuddy/skills/algo-sprite/scripts/gen_bank.py --out 题库汇总.md
python ~/.workbuddy/skills/algo-sprite/scripts/gen_summary.py --out 题目总结.md
```

| 产物 | 内容 | 是否全自动 |
|---|---|---|
| 题库汇总 | 逐题列出题干、选项、✅ 标记的答案、⚠ 坑题、代码题思路 | 是 |
| 题目总结 | 完成情况、知识点题量分布、坑题表、分章题号索引、考点速查 | 骨架自动，考点速查由 AI 基于题号索引补写 |

关键机制：平台题库接口**不返回正确答案**，所以 `submit.py` 每次提交成功会把答案
累积到 `~/.workbuddy/algo-sprite-answers.json`（仓库外，不进公开仓库）。
`--scope done`（默认）只整理已作答章节，`--scope all` 覆盖全部 7 章 332 题。
没有登录令牌时脚本会读本地题库缓存继续出文档，此时平台实时统计标「待核」，不会编数字。

## 目录结构

```
algo-sprite/
├── SKILL.md               # 技能入口：完整工作流说明
├── README.md
├── scripts/
│   ├── login.py           # 登录 + 验证码处理
│   ├── daily_login.py     # 每日登录保分（当天幂等 + 积分快照）
│   ├── fetch_todo.py      # 按章节拉取待做题
│   ├── submit.py          # 批量提交（重试 + 断点续跑 + 答案库累积）
│   ├── report_data.py     # 报告公共数据层
│   ├── gen_bank.py        # 生成题库汇总
│   └── gen_summary.py     # 生成题目总结骨架
└── references/
    └── api.md             # 接口规范、提交格式、章节题量、已知坑题清单
```

依赖：Python 3 标准库（无第三方依赖）。

## 章节题量

| 章节 | 题量 | 题型 |
|---|---|---|
| 第1章 基本概念 | 149 | 单选 |
| 第2章 线性表 | 5 | 单选 + 代码 |
| 第3章 栈和队列 | 17 | 单选 + 代码 |
| 第4章 树与二叉树 | 56 | 单选 + 代码 |
| 第5章 图 | 7 | 单选 |
| 第6章 查找 | 31 | 单选 |
| 第7章 排序 | 67 | 单选 + 代码 |

## 已知坑（详见 references/api.md）

- 平台题目从 Excel 批量导入，**9 道题的判分答案与教材口径不一致**（选项被拆错，判分按原始字母），清单已固化在 `references/api.md`，作答时直接命中
- `tree-63` 为平台错题：正确答案 501 不在选项里，五个选项全判错
- 代码题评测有频率限制（连续提交会被拒，需间隔 60–90 秒），部分题有前置依赖（如 `queue-1` 依赖 `stack-1`）

## 安全约定

- 刷题流程（`login.py`）的学号密码只用于登录请求，**不写入任何文件、日志或总结文档**
- 登录令牌为临时文件，任务完成后自动删除
- 每日自动登录需要无人值守，密码单独存放于**仓库之外**的 `~/.workbuddy/algo-sprite-credentials.json`，权限已收紧为仅当前系统账号可读；`.gitignore` 已排除 `*credentials*.json`，避免误提交
- 答案库 `~/.workbuddy/algo-sprite-answers.json` 与题库缓存同样放在仓库外，`.gitignore` 已排除 `*answers*.json`、`*problems*.json`

## License

仅供个人学习使用。
