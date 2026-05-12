# 写一个 agent（含 skill 白名单）

这一章演示如何从空白模板写出一个完整的 agent、写好 skill 白名单、推到
admin、跑通端到端。我们以 *写一个 `biostat_reviewer`* 为例——专门给
统计审查/biomarker 验证用的 agent。

## Agent 文件结构回顾

agent 在物理层就是一个 `.md` 文件：

```yaml
---
icon: 📊
id: biostat_reviewer
name: Biostat Reviewer
tier: community
toolsets:
  - file_manager
  - web
  - plan
  - think
  - task
  - memory
skills:
  - statistics-check
  - biomarker-roc
  - ic50-fit
  - peer-review
description: |
  Statistical / curve-fitting reviewer. ...
---

You are **Biostat Reviewer** — ...（系统 prompt 正文）
```

详见 [Agent / Team / Toolset 模型](../concepts/01-agent-team-toolset.md)。

## 命名约定

| 场景 | 命名风格 | 例子 |
|---|---|---|
| OmicVerse 自家工作流 agent | `omicverse_<role>` | `omicverse_omni`, `omicverse_expert` |
| 任务驱动 agent | snake_case 短语 | `literature_scout`, `paper_critic`, `clinical_translator` |
| 工作区私有 agent（lab+ 用户） | 任意，建议 `local_<...>` | `local_demo` |

`id` 一旦发布就不要改——它是用户切换 agent 时的稳定句柄、是 conversation
里"上一个回合谁说的"的引用，改了等于断历史。

## 最小可发布的 agent 模板

```markdown
---
icon: 📊
id: biostat_reviewer
name: Biostat Reviewer
tier: community
category: review
category_order: 2
summary: 统计 / 曲线拟合审查员 — 替已完成的分析做最后一道把关。
use_when: 用户跑完 DEG / survival / biomarker / dose-response，想做 final sanity pass 时。
example_prompts:
  - "我刚跑完一个 DEG 分析（n=8, padj<0.05, log2FC>1），帮我审一下统计有没有问题"
  - "帮我看下这个 ROC，AUC 0.78，n=120，结论可不可靠"
toolsets:
  - file_manager
  - web
  - plan
  - think
  - task
  - memory
skills:
  - statistics-check
  - biomarker-roc
  - ic50-fit
  - peer-review
description: |
  Statistical / curve-fitting reviewer. Use when the user has done
  a DEG / survival / biomarker analysis and wants a final sanity pass —
  power, multiple-testing, effect size, ROC, dose-response fits.
---

You are **Biostat Reviewer** — a statistical reviewer for omics
analyses. The user comes to you AFTER they've run an analysis; your
job is to find what's wrong with it before they ship it.

## Routine

1. Restate the analysis. Sample sizes, test, alpha, FDR, effect size,
   power. If any are missing, ask the user explicitly — don't guess.

2. Run `statistics-check` against the design. Common findings:
   - n too small for the claimed effect
   - missing multiple-testing correction
   - effect size not reported
   - test choice mismatched to data type

3. If the analysis involved a biomarker / classifier: run
   `biomarker-roc`. Inspect AUC, DeLong CI, calibration if relevant.

4. If it involved dose-response data: run `ic50-fit`. Check for poor
   curve fits, hill-slope outside the plausible range, leverage points.

5. Wrap with `peer-review` formatting — Strengths / Weaknesses /
   Major / Minor / Recommendation.

## Output

Markdown with these exact section headers — downstream tooling parses
them.

- **TL;DR**
- **Statistical sanity**
- **Biomarker / fit results** (if applicable)
- **Recommendation**: `accept | minor revisions | major revisions | reject`

## What you don't do

- Don't write the original analysis — you're reviewing what already
  exists.
- Don't run literature search — delegate to `literature_scout`.
- Don't audit code reproducibility — delegate to `paper_critic`.
```

## 模板中的关键字段

### `description` / `summary` / `use_when` / `example_prompts`

这四个字段都是给 SPA 卡片用的——**LLM 一个都不读**（LLM 读的是
`---` 之后的正文）。区别：

| 字段 | 用途 | 写作风格 |
|---|---|---|
| `description` | 英文一行，admin 早期就有 | 名词短语 + 动词短语，≤ 280 字符 |
| `summary` | 中文一行，2026-05 新增（PR admin #12） | "我是谁 + 我的一句话价值" |
| `use_when` | "什么时候选我" | 用户视角的场景描述，单句 |
| `example_prompts` | 卡片底部一键示例 | 用户口吻 ≤ 30 字的提问，2-3 条 |

为什么要四个字段？因为 SPA Agent 卡片的不同位置有不同显示：标题旁是
`summary`，hover 出来的浮层是 `use_when` + `example_prompts`，
description 用作 fallback / 兼容老客户端。

### `toolsets`

参考 [Agent / Team / Toolset 模型 § Toolset](../concepts/01-agent-team-toolset.md#toolset)。

最少配置：`file_manager + web + plan + think + task + memory`。这套
覆盖几乎所有 *non-execution* agent 的需要。要跑代码再加
`integrated_notebook`。

### `skills` 白名单

回忆 [Skill 系统 § 白名单](../concepts/02-skills-system.md#白名单agent--skill-绑定)：

- **空 / 缺失** — 看到全部 skill。**只用在编排员**（`omicverse_omni`）。
- `["*"]` — 显式通配，同上。
- 命名列表 — 严格白名单。**所有专精 agent 都用这种**。

写专精 agent 时：

1. 先列出这个 agent 一次对话**真正需要**的 skill。
2. 不要把所有可能用到的都塞进来——多余的 skill 描述会污染 system prompt
   的 token，模型还可能误调。
3. 4–6 个 skill 是甜区。超过 8 个考虑要不要拆成两个 agent。

### 系统 prompt 正文（`---` 之后）

OmicOS 没强制结构，但实践下来三段最稳：

```markdown
You are **<name>** — <一句话身份>。

## Routine

<step-by-step 工作流，明确点名什么时候调什么 skill>

## Output

<规定 output 格式 — markdown 标题 / json 字段 / 表格 schema>

## What you don't do

<明确划清边界，避免和其它 agent 抢活>
```

`Routine` 段里**点名 skill** 是关键。不要写"use search to find"，写
"use `pubmed-search` skill"——LLM 看到具体名字才会调对应的 playbook。

## 推到 admin

```bash
# 1. 写到本地暂存
mkdir -p /tmp/agents-import
$EDITOR /tmp/agents-import/biostat_reviewer.md

# 2. 上传
scp /tmp/agents-import/biostat_reviewer.md \
    root@23.226.134.91:/var/omicos-admin/agents/

# 3. 修对所有权
ssh root@23.226.134.91 \
    "chown 501:staff /var/omicos-admin/agents/biostat_reviewer.md"

# 4. 验证 — admin 端有版本号
ssh root@23.226.134.91 \
    "curl -s http://127.0.0.1:5070/api/public/agents/manifest | \
     python3 -m json.tool"
```

```{admonition} admin 自动版本化
:class: tip

每次 admin 收到 agent 改动会把旧版本归档到
`/var/omicos-admin/agents/.versions/<id>/<timestamp>.md`，便于回滚。
skill 不归档，所以 skill 改动建议先本地 git。
```

## 客户端拉到

桌面端下次启动会自动同步，或：

```bash
curl -X POST http://127.0.0.1:<sidecar-port>/api/agents/refresh
```

验证：

```bash
cat ~/.omicos/cloud-agents/agents/biostat_reviewer.md
```

## 删 / 改名 agent

- **改名**：`id` 一旦发布就别改。如果非要改，admin 老 id 留一个
  `description: |\nDeprecated, use new_id` 的占位 stub，避免老对话
  里的"上一个回合是 X"指向消失的 agent。
- **删除**：直接 `rm /var/omicos-admin/agents/<id>.md`。下次客户端
  sync 会从 cache 也删掉。同上，建议留 stub。

## 故障排查

| 现象 | 原因 |
|---|---|
| 卡片不显示 | description 空，或 frontmatter 解析失败（YAML 缩进错）；`curl /api/public/agents/<id>` 看后端解析结果 |
| skills 字段没生效（LLM 还看到全部） | admin Python 没把 `skills` 加到 `_PROJECTED_KEYS`——参考 PR #117 的 patch |
| LLM 切到这个 agent 后表现没变 | 正文太短、太通用——agent 的"灵魂"在系统 prompt，前 200 字决定 80% |
| Tool call 报 "unknown skill" | skill id 拼错；先到 `~/.omicos/cloud-skills/skills/<id>/SKILL.md` 确认本地缓存 |

## 进一步

- [Agent / Team / Toolset 模型](../concepts/01-agent-team-toolset.md) — 概念
- [写一个 skill](01-add-a-skill.md) — 配套
- [加一个 toolset](04-add-a-toolset.md) — 当现有 toolset 不够用时
