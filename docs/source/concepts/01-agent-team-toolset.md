# Agent / Team / Toolset 模型

OmicOS 的 LLM 编排有三个核心抽象。理解它们之间的关系比理解任何具体
模块都重要——所有的扩展点（加 skill、加 provider、加工具）最终都映射到
这三个名字之一。

## Agent

一个 **agent** = 一份 *系统 prompt* + 一份 *toolsets 白名单* +
一份 *skills 白名单* + 一个 *tier 标记*。它在物理层面就是一个
Markdown 文件，frontmatter 描述能力，正文是 system prompt。

```yaml
---
icon: 🔍
id: literature_scout
name: Literature Scout
tier: community
category: literature
category_order: 2
summary: 文献侦察员 — 给一个领域，回一份近期重要论文 + 撤稿风险扫描。
use_when: 用户要做 lit review、对比近期工作、查作者过往撤稿史时。
example_prompts:
  - "调研一下最近 colorectal cancer immunotherapy 的进展。"
  - "这个作者过去 5 年的论文里有没有被 retract 的？"
toolsets:
  - file_manager
  - web
  - plan
  - think
  - task
  - memory
skills:
  - pubmed-search
  - biorxiv-monitor
  - retraction-check
  - source-comparison
---

You are **Literature Scout** — a biomedical literature reconnaissance
specialist. ...（正文是它的人格 + 工作流）
```

| frontmatter 字段 | 含义 |
|---|---|
| `id` | 程序内部使用的稳定 id，全局唯一。**改了等于换 agent**。 |
| `name` | UI 显示用的人类名字 |
| `icon` | 单 emoji 字符，UI 卡片头像 |
| `tier` | `community` / `pro_agent` / `pro_cloud` / `lab` / ...，决定订阅门槛 |
| `category` | 分类 id（如 `single_cell_analysis`、`literature`），决定 SPA Agent 页放哪一行 |
| `category_order` | 同分类内的排序（小者靠前）；分类内最小值还决定该分类整行的优先级 |
| `summary` | SPA Agent 卡片中文副标题，**LLM 不读** — 仅 UI 用 |
| `use_when` | SPA 卡片"什么时候选我"的提示行，**LLM 不读** |
| `example_prompts` | SPA 卡片底部的示例提问，点一下塞进 composer |
| `toolsets` | 这个 agent 能用的工具 *组*——见下文 |
| `skills` | 这个 agent 能看到的 skill *白名单*——见 [Skill 系统](02-skills-system.md) |
| 正文 | system prompt（去掉 frontmatter 后整段塞给 LLM） |

```{admonition} summary / use_when / example_prompts 是 UI-only
:class: tip

这三个字段从 2026-05 才加进来，**不进 system prompt**，纯粹给前端
卡片展示用（PR omicos-core #120 + admin #12）。`description` 仍然
是 LLM 看不到、SPA 看得到的"短简介"——但它是英文 + 一行的设计，
中文长简介推荐用 `summary`，触发场景用 `use_when`。
```

agent 文件的来源有三处，按优先级（早者覆盖晚者）：

1. **工作区本地**：`<workspace>/agents/<id>.md`（lab+ tier 才会读）
2. **legacy 工作区**：`<workspace>/.omicos/agents/<id>.md`
3. **云端缓存**：`~/.omicos/cloud-agents/agents/<id>.md`（从 admin 同步）

源码：[`omicos-core/src/agents.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/agents.rs)
里的 `AgentSpec` + `TemplateStore::load_agent`。

## Team

一个 **team** = 当前对话激活的一组 agent + 一个 *active agent*。
team 由 SPA 在每次 chat 请求时通过 `team_members: ["a", "b"]`
+ `agent: "a"` 指定，sidecar 用这两个字段加载具体的 `AgentSpec` 列表
（其中 active agent 是当前回合发声的那个）。

```rust
pub struct TeamRuntime {
    pub active_agent: AgentSpec,
    pub agents: Vec<AgentSpec>,
}
```

### `call_agent` —— team 内代理切换

team 里的非 active agent 不是摆设。当 active agent 在 system prompt
里看到 "Available agents: ..." 时，它可以调
`call_agent { agent_name: "expert", instruction: "..." }` 工具把当
前任务委托给 team 里的另一个 agent。sidecar 拦截这个 tool call，
*以 expert 为 active agent 重新跑一个子回合*，结果回填给原 caller。

这套机制让你可以做出经典的 "Omni 编排员 → Expert 干活" 模式而不用
离开同一个对话。每个 agent 看到的工具集与 skill 集都是 *自己的*——
切换是 *上下文重建*，不是 *权限继承*。

### 默认 team

```{admonition} 2026-05 起：默认 team = admin catalog
:class: important

PR omicos-core #119 之后，sidecar **不再硬编码** `[omni, expert, spatial]`
兜底，也**不再强制把 `omicverse_omni` 注入**当前 team。`resolve_team`
逻辑是：

- 如果 SPA 传了非空 `team_members`：以它为准（PR #121 修复了之前 SPA
  挑了子集 sidecar 仍然加载全部的 bug）。
- 如果 SPA 没传：sidecar 用 admin cloud catalog 里**当前全部** agent
  作为 team 候选 —— Omni 是不是被包括完全取决于 admin 现在还发不发它。
- catalog 里找不到的 id（旧对话历史里的"前一回合是 X"指向已删除的
  agent）会被构造成一个 `default_agent` 占位符，避免 prompt 渲染崩。
```

CLI（`omicos chat`、`omicos cli_chat`）也走同一套逻辑，没有任何
"内置兜底 team" 的概念了。

## Toolset

一个 **toolset** = 一组工具的命名集合。每个工具最终是 sidecar
内部的某个 Rust 函数（`fn run_python_code(...)`）或一段 native 调用
（`fn web_search(...)`）。toolsets 让 agent 模板能用一行
`- web` 拉起 *web_search + web_fetch + ...* 一整组工具，而不必把
每个底层工具列出来。

工具组的物理定义在
[`tool_providers/mod.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/tool_providers/mod.rs)：

```rust
const TOOLSET_GROUPS: &[(&str, &[&str])] = &[
    ("integrated_notebook", &["python", "notebook", "omicverse_lookup"]),
    ("web", &["web_search", "web_fetch"]),
    ("file_manager", &[
        "file_manager__list", "file_manager__read",
        "file_manager__write", "file_manager__edit",
        "file_manager__glob", "file_manager__grep",
    ]),
    // ...
];
```

每个 agent 的 frontmatter `toolsets:` 列出来的名字会被这张表展开成
具体的 tool 列表。LLM 看到的 *function tools* schema 就是从这个
展开后的列表生成的。

### 运行时自动追加

某些 toolset 是平台保留的，sidecar 在每次请求构建 prompt 时自动
追加，agent 模板不用列：

| 自动追加的 toolset | 触发条件 |
|---|---|
| `team` | team 里有 ≥2 个 agent 时，让 LLM 能调 `call_agent` |
| `skill` | 当 skill catalog 非空时，让 LLM 能调 `skill { name }` |
| `memory` | 总是追加，提供 memory 读写 |

源码：`tool_providers::apply_runtime_toolset_defaults`。

## 三个抽象的关系

::::{admonition} 一张图记住
:class: tip

```
Team
└── active AgentSpec
    ├── system prompt   (frontmatter 正文)
    ├── toolsets[]      → 展开成具体 tools → LLM function-call schema
    ├── skills[]        → 过滤 skill catalog → LLM 看到的 skill 名单
    └── tier            → 订阅门槛
```

LLM 的可见能力 = `tools(toolsets) ∪ skills(whitelist) ∪ team-mates`。
::::

## 加新 agent / toolset 的入口

- 加新 agent：[扩展开发 / 写一个 agent](../extension-guides/02-add-an-agent.md)
- 加新 toolset：[扩展开发 / 加一个 toolset](../extension-guides/04-add-a-toolset.md)
- agent 想要新的 skill：先 [写一个 skill](../extension-guides/01-add-a-skill.md)，
  再把 id 加到 frontmatter 的 `skills:` 列表
