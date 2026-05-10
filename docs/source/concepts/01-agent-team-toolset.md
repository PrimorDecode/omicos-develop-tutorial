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
| `toolsets` | 这个 agent 能用的工具 *组*——见下文 |
| `skills` | 这个 agent 能看到的 skill *白名单*——见 [Skill 系统](02-skills-system.md) |
| 正文 | system prompt（去掉 frontmatter 后整段塞给 LLM） |

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

如果 SPA 没传 `team_members`：

```rust
vec![
    "omicverse_omni".to_string(),
    "omicverse_expert".to_string(),
    "omicverse_spatial".to_string(),
]
```

这是 CLI 和老前端的兜底。新的桌面端总是显式传 team。

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
