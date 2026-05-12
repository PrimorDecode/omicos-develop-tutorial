# 写一个 skill

本章演示从零写一个 skill、把它推到 admin、让 OmicOS 客户端拉到、
绑定给某个 agent，整个流水线走通一次。我们以 *给 `paper_critic` 加
一个 GitHub-stars-history skill* 为例——agent 要审一篇论文时，
拉它配套仓库的 star 时间序列辅助判断社区接受度。

## Skill 文件结构回顾

```
<skill-id>/
├── SKILL.md       # 必需：name + description + 正文
└── reference.md   # 可选：附录文档（不会自动加载）
```

`SKILL.md` 没有"模板"——内容由你决定，但有些套路在 OmicOS 已经形成
惯例。

## 1. 想清楚 description 怎么写

回忆 [Skill 系统](../concepts/02-skills-system.md)：description 就是
搜索引擎。LLM 决定调不调你的 skill 完全靠这一行。三条经验：

| 反例 | 正例 |
|---|---|
| `Skill for github` | `Pull a GitHub repository's star-history time series via star-history.com / API. Use when judging a paper's open-source impact.` |
| `Helper for trials` | `Search ClinicalTrials.gov by condition / drug / phase. Returns trial NCT ID, status, primary endpoint, sponsor.` |
| `Generic pubmed wrapper` | `Search PubMed with MeSH terms, structured queries, filters. Use for peer-reviewed biomedical literature, systematic reviews, meta-analyses.` |

**写法规范**：

- 第一句说**做什么**（动词开头）
- 第二句说**什么时候用**（用户场景）
- 总长 ≤ 280 字符——SPA 卡片里截断后还能读懂

## 2. 写 SKILL.md 正文

正文是 LLM 真正会执行的指令。同样有惯例：

- **从结构化指令开始**——表格列出可用命令、推荐查询模板
- **明确 output 格式**——告诉 LLM 该返回 markdown / json / 哪些字段
- **list "what you don't do"**——避免越权执行其它 skill 的工作

下面是我们 demo skill 的完整内容：

```markdown
---
name: github-star-history
description: Fetch a GitHub repo's star-history time series via star-history.com API. Use when assessing community uptake of an open-source paper companion repo or comparing momentum across similar projects.
category: literature
category_order: 5
summary: 拉一个 GitHub 仓库的 star 时间序列，判断社区接受度。
use_when: 给论文配套仓库 / 工具仓库做"势能"评估时。
example_prompts:
  - "评估 https://github.com/scverse/scanpy 的社区势能"
---

# GitHub Star History

Pull star count over time for a GitHub repository. Useful when auditing
a paper that ships code — flat or declining stars suggests the project
isn't being maintained even if the paper is hot.

## Commands

| Command | Description |
|---------|-------------|
| `web_fetch "https://api.star-history.com/svc/repos/<owner>/<repo>"` | JSON: stars per timestamp |
| `web_search "site:github.com <owner>/<repo> stars"` | sanity-check the repo exists |

## Workflow

1. Resolve the repo URL the user gave you (paper supplement, README link).
2. Pull the star-history time series.
3. Compute three numbers: total stars, slope over the last 90 days,
   max single-day delta.
4. Surface the inflection points (release dates, paper publication date
   if known) and call out whether momentum is accelerating, plateaued,
   or declining.

## Output

```
Repo:       <owner>/<repo>
Total:      <N> stars
Last 90d:   +<N> (Δ slope vs prior 90d)
Inflection: <date>: <event>
Verdict:    accelerating | plateaued | declining
```

## What this skill DOES NOT do

- Audit code quality — that's `paper-code-audit`.
- Pull commit / contributor stats — out of scope.
- Render a chart — text only.
```

把它存成 `/tmp/new-skills/github-star-history/SKILL.md`。

```{admonition} frontmatter 字段一览
:class: note

| 字段 | LLM 读？ | 用途 |
|---|---|---|
| `name` | ✓ | skill 稳定 id，**必须**等于目录名（admin #36 起自动归一化） |
| `description` | ✓ | 一行英文发现描述——LLM 决定调不调就靠它 |
| `category` | ✗ | SPA Skills 页分类行；和 Agent 同一套机制 |
| `category_order` | ✗ | 同分类内排序 |
| `summary` | ✗ | SPA 卡片中文副标题 |
| `use_when` | ✗ | SPA 卡片"什么时候用"提示 |
| `example_prompts` | ✗ | SPA 卡片底部一键塞 composer |

`summary` / `use_when` / `example_prompts` 是 2026-05 才加的 UI 字段，
LLM 看不到，纯粹给用户挑 skill 时看。
```

## 3. 推到 admin 服务器

skill 的**唯一权威**是 admin 服务器。本地手工放进
`~/.omicos/cloud-skills/` 也能跑，但下次 sync 会被 GC 删掉。
（**`~/.omicos/skills/`** 这个家目录 root 在 2026-05 已经移除——
见 [Skill 系统 § 4 个发现根](../concepts/02-skills-system.md)。）

```bash
# 上传到 admin 数据目录
scp -r /tmp/new-skills/github-star-history \
    root@23.226.134.91:/var/omicos-admin/skills/

# 修对所有权 + 用 admin 的 uid 一致
ssh root@23.226.134.91 \
    "chown -R 501:staff /var/omicos-admin/skills/github-star-history"

# 不需要重启 Flask —— 它每次请求重扫 SKILLS_DIR
ssh root@23.226.134.91 \
    "curl -s http://127.0.0.1:5070/api/public/skills/manifest | \
     python3 -c 'import json,sys;d=json.load(sys.stdin);print(len(d[\"skills\"]))'"
```

应该看到 skill 数量 +1。

```{admonition} 更舒服的 admin SPA 路径
:class: tip

2026-05 的 admin 端有了**文件夹感知**的 skill 管理（PR admin #25、#26）：
直接打开 admin 面板 → Skills → 上传 / 新建文件夹 / 改名 / 嵌套——
所有 CRUD 都在 UI 完成，不用 scp。改名时 `name:` frontmatter 会被
自动同步到新 dirname（PR admin #36）。
```

## 4. 绑给 agent

skill 同步到客户端后默认是"在云 catalog 里"——但如果对应 agent 写了
`skills:` 白名单且没列你这个 skill，**LLM 看不到它**（[Skill 系统 §
白名单](../concepts/02-skills-system.md#白名单agent--skill-绑定)）。

编辑 agent 的 `.md`，把 id 加到 frontmatter `skills:` 列表里：

```diff
 skills:
   - paper-code-audit
   - replication
   - statistics-check
   - peer-review
   - retraction-check
+  - github-star-history
```

推到 admin：

```bash
scp /tmp/agents-import/paper_critic.md \
    root@23.226.134.91:/var/omicos-admin/agents/

ssh root@23.226.134.91 \
    "chown 501:staff /var/omicos-admin/agents/paper_critic.md"
```

```{admonition} 不修改 agent 的话怎么样
:class: note

如果你的 skill 想给 *所有* agent 用，把它加到 `omicverse_omni`
（用 `skills: ["*"]` 通配符）的工作场景就够了——它本来就全开。

如果你想给 *workspace 本地* 测试，把 `SKILL.md` 放
`<workspace>/skills/github-star-history/SKILL.md`，**任意 agent 都
能看到**——workspace skill 不受白名单限制（lab+ tier）。
```

## 5. 客户端拉同步

桌面端启动时自动同步。手动触发：

```bash
# Sidecar 暴露的接口
curl -X POST http://127.0.0.1:<sidecar-port>/api/skills/refresh
```

或者在 SPA 的"技能"页点"刷新"按钮——一回事。

验证本地缓存：

```bash
ls ~/.omicos/cloud-skills/skills/github-star-history/
# 应该看到 SKILL.md
```

## 6. 跑一次

新开对话、active agent 选 `paper_critic`、给个仓库链接，例如：

```
帮我评估 https://github.com/scverse/scanpy 的社区势能。
```

LLM 读 system prompt 看到 `github-star-history` 在白名单里、
description 说"Use when assessing community uptake"——切中场景，应该
直接调。

如果它没调，回去检查 description 是否切题——发现机制就靠那一行。

## 故障排查

| 现象 | 原因 |
|---|---|
| skill 在 admin 有但客户端 catalog 没有 | sync 没跑成功；`POST /api/skills/refresh` 看 manifest 版本 |
| LLM 在 prompt 里看不到（no roster entry） | agent 白名单没加，或 description 太空被截掉 |
| `skill { name }` 返回 unknown | 同上 + skill id 拼写错（注意横杠 vs 下划线） |
| skill 加载了但 LLM 不照办 | 正文里 imperative 不够强；试着首段写 "Use the commands below as your only path." |

## 带附件文件的 skill

如果你的 skill 需要 templates、reference 文档、CSV/JSON schema 等
附件，直接放在 skill 目录里：

```
github-star-history/
├── SKILL.md
├── reference.md              # 给人看的额外文档（admin 用作版本变更说明）
├── templates/
│   └── summary.md.tmpl       # LLM 用 skill_resource 加载
└── examples/
    └── scanpy_response.json
```

admin `?include_files=1` 会把整个目录打包返回，客户端
`cloud_skills.rs` 完整镜像到 `~/.omicos/cloud-skills/skills/<id>/`。
SKILL.md 正文里指点 LLM 主动调用：

```markdown
When generating the final summary, fetch the canonical template via
`skill_resource { name: "github-star-history", relpath: "templates/summary.md.tmpl" }`
and fill it in.
```

详见 [Tool pipeline § skill_resource](../omicos-core/04-tool-pipeline.md)。

## 进一步阅读

- [Skill 系统设计](../concepts/02-skills-system.md)
- [写一个 agent](02-add-an-agent.md) — 配套绑定
- [Tool pipeline](../omicos-core/04-tool-pipeline.md) — `skill_resource` 工具
