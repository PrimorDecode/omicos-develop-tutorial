# Skill 系统：发现 → 白名单 → 执行

OmicOS 的 skill 系统借鉴自 Anthropic 的 Claude Code：每个 skill 是一个
**Markdown playbook**，平时不进 system prompt，需要时由 LLM 主动调
`skill { name: "X" }` 工具加载它的正文，把它当成「这一回合临时附加的
指令」执行。

这套设计避免了把所有 playbook 都塞进 system prompt 导致的 token 爆炸，
让 skill 数量可以横向扩展到几十甚至上百个。

## Skill 的物理形态

每个 skill 就是一个目录：

```
<root>/<id>/
├── SKILL.md       # 必需：frontmatter + 正文
└── reference.md   # 可选：辅助文档，不会自动加载
```

`SKILL.md` 的 frontmatter 现在长这样：

```yaml
---
name: pubmed-search
description: Search PubMed with MeSH terms, structured queries, and filters. Use for peer-reviewed biomedical literature, ...
category: literature
category_order: 1
summary: 一句中文卡片副标题（UI 用，LLM 不读）
use_when: 用户问"找最近 ... 的论文"、要做 lit review、对比近期工作时。
example_prompts:
  - "找最近 colorectal cancer immunotherapy 的论文"
---

# PubMed Search

Use PubMed via web search or NCBI E-utilities for ...
```

字段表：

| 字段 | LLM 看得到？ | 用途 |
|---|---|---|
| `name` | ✓ | skill 的稳定 id，全局唯一。LLM 调 `skill { name: "<这个名字>" }`。**必须**与目录名匹配——PR omicos-admin #36 起 admin 端会自动归一化 |
| `description` | ✓ | 一句话英文能力描述。**这是发现机制**——LLM 通过它判断该不该调 |
| `category` | ✗ | 分类 id，决定 SPA Skills 页放哪一行（与 Agent 同一套机制） |
| `category_order` | ✗ | 同分类内的排序；分类内最小值决定该分类整行的优先级 |
| `summary` | ✗ | SPA 卡片中文副标题。2026-05 新增（PR omicos-core #132） |
| `use_when` | ✗ | SPA 卡片"什么时候用"提示行 |
| `example_prompts` | ✗ | SPA 卡片底部示例提问 |

```{admonition} description 仍然是发现的唯一渠道
:class: tip

不要把 description 当成"补充说明"——它**就是** skill 的搜索引擎。
LLM 决定调哪个 skill 完全靠这一行。description 没写好 = skill 永远
被忽略。当你新加一个 skill 而 LLM 从来不调它，先回去读自己的
description。

`summary` / `use_when` 是给**人**看的，不是给 LLM 看的。
```

## 4 个发现根（2026-05 后）

skill 不止一处来源。sidecar 启动时按这个顺序扫描，**早者覆盖晚者**
（同名 skill 第一个出现的赢）：

| 优先级 | 路径 | 用途 |
|---|---|---|
| 1 | `OMICOS_SKILL_ROOTS`（环境变量，`:` 分隔多个路径） | 测试 / dev override |
| 2 | `~/.omicos/cloud-skills/skills/<id>/SKILL.md` | 从 admin 同步的云端 skill |
| 3 | `<workspace>/skills/<id>/SKILL.md` | 工作区本地（lab+ 订阅才扫） |
| 4 | `<workspace>/.omicos/skills/<id>/SKILL.md` | legacy 工作区路径（lab+） |

源码：[`omicos-core/src/skills/mod.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/skills/mod.rs)
的 `default_skill_roots()`。

```{admonition} 我们删掉了什么
:class: warning

历史上还有：

- 第 5、6 个根：从 Python `omicverse_skills` pip 包里读 60+ 内置 skill —
  PR omicos-core #114 移除。
- 第 7 个根：`~/.omicos/skills/`（用户家目录 user-global skills）—
  PR omicos-core #116 移除。原因是它跨工作区"漏"出来：在一个 workspace
  写的内部 skill 出现在另一个 workspace 的 catalog，违反"工作区即隔离单位"的承诺。

**今天的规则简单：skill 只有两种来源 — cloud（admin）或 workspace。**
没有用户家目录的中间层。
```

### 同步算法的关键不变量

`SkillCatalog::discover` 和 SPA 走的 `/api/skills` 在历史上曾经**漂移**：
一份递归 100 层，把任意 `.md` 都当 skill；另一份只认 `<id>/SKILL.md`。
PR #115 把两者对齐到同一形状：

> **一个目录 = 一个 skill；一个 root 只下钻一层；必须存在 `SKILL.md` 才算。**

如果你以后要改 skill 发现，**两份实现要同步改**，否则 SPA 与 LLM 会
对"什么是 skill"产生不同答案。

(skill-resource-tool)=
## skill_resource — 读 skill 目录里的其它文件

skill 不只 `SKILL.md`。playbook 可以附带 `reference.md`、JSON
schema、模板 SQL 等等。SKILL.md 默认通过 `skill { name }` 工具加载
正文；想读同目录的其它文件就用 PR omicos-core #129 加的
`skill_resource` 工具：

```json
{ "name": "skill_resource",
  "arguments": {
    "name": "report-html-generation",
    "relpath": "templates/cover.html"
  } }
```

实现细节：

- 拒绝 `..`、绝对路径、隐藏路径段（`.git/...`），只能在 skill 目录内
- UTF-8 文件直接返回 `content`；二进制返回 `content_b64`
- 文件超过 1 MB 返回 `truncated: true`

`SKILL.md` 正文里可以指点 LLM 主动调它："Use `skill_resource` with
relpath `templates/cover.html` to fetch the cover template."

## 白名单：agent ↔ skill 绑定

光有发现不够。当 admin 上有 30 个 skill，但某个 agent 只该看 4 个
（比如 `literature_scout` 只该看文献检索类）——这就是 *agent.skills*
白名单的工作。

agent frontmatter：

```yaml
skills:
  - pubmed-search
  - biorxiv-monitor
  - retraction-check
  - source-comparison
```

sidecar 在每次 turn 用 `SkillCatalog::filter_for_agent(&agent.skills)`
过滤一次，过滤后的 catalog **同时给 system prompt 和 skill 工具
provider 用**。这意味着：

- **roster summary 只列白名单 skill** — LLM 看不到名单外的 skill
  描述，连"该不该调"的判断都不会发生
- **`skill { name: "X" }` 调用如果 X 不在白名单 → "unknown skill" 错误**——
  即便 LLM 凭训练数据猜出某个 skill 名也调不到

### 白名单的 3 种形态

| `skills:` 写法 | 语义 |
|---|---|
| `skills: ["a", "b"]` | 严格白名单：只看到 a + b（外加所有 workspace 本地 skill） |
| `skills: ["*"]` | 显式通配：看到全部。`omicverse_omni` 编排员用这个保持全权 |
| `skills:` 字段缺失或空列表 | 同 `["*"]`，向后兼容老 agent 模板 |

### 为什么 workspace 本地 skill 总是可见

不论白名单怎么写，`<workspace>/skills/` 里用户自己写的 skill **永远**
进入 catalog。理由：那是用户在自己机器上自己写的文件，让 admin 端
curated agent 来决定该不该可见，是反直觉的 UX。

源码：`SkillCatalog::filter_for_agent` 里的：

```rust
let always_on = matches!(spec.source.as_str(), "project" | "project_legacy");
if wildcard || always_on || allowed.contains(spec.name.as_str()) {
    out.skills.insert(name.clone(), spec.clone());
}
```

## 一次完整的 skill 调用回合

1. sidecar 启动 → 同步 admin → 把 cloud-skills 写到 `~/.omicos/cloud-skills/`。
2. 用户开新对话、选 agent `literature_scout`。
3. 用户发消息 → sidecar 构建 prompt：
   - 读 `AgentSpec` → 得到 `skills: [pubmed-search, biorxiv-monitor, ...]`
   - `SkillCatalog::discover` → 全部 11 个云 skill
   - `filter_for_agent(&agent.skills)` → 过滤到 4 个
   - `roster_summary()` → 拼成 system prompt 末尾的：
     ```
     ## Available skills
     - `pubmed-search` — Search PubMed with MeSH terms ... [cloud]
     - `biorxiv-monitor` — ...
     - `retraction-check` — ...
     - `source-comparison` — ...
     ```
4. LLM 阅读用户问题"找最近 colorectal cancer immunotherapy 的论文"
   → 决定调 `skill { name: "pubmed-search" }`。
5. sidecar 的 `SkillProvider::call_tool` → `catalog.load_body("pubmed-search")`
   → 读 `~/.omicos/cloud-skills/skills/pubmed-search/SKILL.md` 的正文
   （去除 frontmatter）→ 包装成：
   ```
   Loaded skill `pubmed-search`. Treat the markdown below as instructions
   to follow for the rest of this turn. ...
   ----- BEGIN SKILL -----
   <SKILL.md 正文>
   ----- END SKILL -----
   ```
6. 工具结果回到 LLM，作为下一轮 prompt 的一部分；LLM 按 playbook 指引
   执行——调 `web_search`、组合 MeSH query、整理 markdown 输出……

## 同步：从 admin 到本地缓存

skill 不在 git 仓库里跟 sidecar 一起发布，而是从 admin 服务器拉。

- **manifest 端点**：`GET /api/public/skills/manifest` 返回
  `{skills: [{id, hash, tier, updated_at, dirname}], version}`。
  PR omicos-core #132 新增 `dirname` 字段——便于 admin 改文件夹名
  时本地缓存能跟着改人类目录名，但**稳定 id 仍然是 `id`**。
- **客户端缓存**：`~/.omicos/cloud-skills/manifest.json` 记录上次拉到的
  版本与每个 skill 的 hash。
- **同步策略**：客户端比较 hash → 改动的 skill 才重新拉
  `GET /api/public/skills/<id>` → 写到
  `~/.omicos/cloud-skills/skills/<id>/SKILL.md`。
- **GC**：服务器不再发布的 skill id 会从本地缓存删除。

源码：[`omicos-core/src/cloud_skills.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/cloud_skills.rs)。

### raw_md 字节级镜像（2026-05 起）

PR omicos-core #124 之后，客户端**逐字节**写入 admin 返回的 `raw_md`
字段——不再走"解析 frontmatter → 反序列化重写"那一道。

为什么：那道往返会把客户端不认识的 frontmatter 字段（比如某次新增
的 `team_pref` 还没发版本）**默默丢掉**，下一次 reparse 就缺字段，
回头同步 hash 还能对得上、但内容不对了。

现在 cache 是 admin 文件的**完整副本**——admin 写什么，本地存什么，
不认识的字段保留下来，等客户端版本更新后自动解析。PR #123 顺手修
了同一个问题在 category / category_order 上的偷字段 bug。

### hash 现在覆盖整个 skill 目录

历史上 skill hash 只是 `SKILL.md` 的 blake2b。PR omicos-admin 改成
sha256 over `(SKILL.md body, sorted (resource_path, content))`——
意味着改 `reference.md` 或者新增 `templates/cover.html` 都会触发
增量同步。配合上面的 `?include_files=1`（见
[admin 公开 API](../omicos-admin/02-public-api.md)），客户端能完整
拷贝整个目录而不仅仅是 `SKILL.md`。

### Permanent rejection 后游标推进

PR omicos-core #131 修了一个潜在的"无限循环重试"。conversation /
trajectory 这类**写**接口如果返回 `AppendOutcome::Permanent`（比如
4xx schema 错误），sidecar 现在会把游标推进到这一批末尾，**跳过**
这批不可恢复的 batch；之前会把游标卡在出错那批，下次同步又重发，
又被拒，循环。

## 想自己加一个 skill？

跳到 [写一个 skill](../extension-guides/01-add-a-skill.md)。
