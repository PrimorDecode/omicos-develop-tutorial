# Goal 模式（长时程任务）

2026-05 起 omicos-core 加了一套 *long-horizon goal* 子系统，
对齐 codex / claude code 的 `/goal` 体验。

> 一句话动机：让用户写一句"帮我把这份 bulk RNA 数据从 fastq 跑到
> 文章级 figure"，sidecar 自己**一回合接一回合**跑下去，跑到达成
> 目标 / 超预算 / 用户喊停才停。

源码：
[`omicos-core/src/goals.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/goals.rs)
+ [`goal_templates.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/goal_templates.rs)
+ `native.rs` 的 `/api/threads/:session_id/goal` 路由。

## Goal 的状态机

```text
        create
          │
          ▼
       ┌──────┐  pause   ┌────────┐
       │Active│ ───────▶ │Paused  │
       └──┬───┘ ◀─────── └────────┘
          │     resume
   tokens >= budget
          ▼
   ┌──────────────┐
   │BudgetLimited │   ←—— 自动转入，需要 resume + 加预算才能继续
   └──────────────┘
          │  complete (model 调 update_goal)
          ▼
       Complete
```

四种状态在 wire 上是 snake_case：`active` / `paused` / `budget_limited` /
`complete`。

## 持久化

Goal 是**每个 thread 一条**，写在 thread `meta.json` 的 `goal` 字段。
shape：

```json
{
  "goal": {
    "goal_id": "f7c8...",   // UUIDv4 — 乐观锁
    "objective": "Bulk RNA-seq end-to-end on GSE166925, finish to figure-grade plots.",
    "status": "active",
    "token_budget": 500000,
    "tokens_used": 129036,
    "tokens_in_used": 126345,
    "tokens_out_used": 2691,
    "created_at": "2026-05-12T10:11:00Z",
    "updated_at": "2026-05-12T10:34:21Z"
  }
}
```

`goal_id` 在 PATCH 时必须带回去匹配——目标是防 SPA / CLI / 自动续跑
同时改一份 goal 时的 lost-update。`clear` 是个例外，不要求匹配。

## HTTP / Tool 接口

| 方向 | 接口 | 用途 |
|---|---|---|
| SPA → sidecar | `GET  /api/threads/:sid/goal` | 拉当前 goal |
| SPA → sidecar | `POST /api/threads/:sid/goal` `{objective, token_budget?}` | 新建 |
| SPA → sidecar | `PATCH /api/threads/:sid/goal` `{action, expected_goal_id?}` | pause / resume / clear / complete |
| LLM → sidecar（tool） | `create_goal` | 同 POST。**模型不能擅自创建**——只有 system prompt 明确允许的 agent 才暴露 |
| LLM → sidecar（tool） | `get_goal` | 自检：现在还剩多少预算、状态是什么 |
| LLM → sidecar（tool） | `update_goal { complete: true }` | 模型自己宣布完成，触发停回合 |

```{admonition} 模型只能 complete，不能 pause / clear
:class: warning

`update_goal` 工具暴露给 LLM 只是为了**模型自己宣布完成**——以及读
budget。pause / clear 必须走 SPA → 用户在 UI 点。这是设计选择，避免
模型说"任务结束了"然后立刻把 goal 清掉、用户后来再发消息时看到一
个空状态。
```

## continuation engine —— 自动续回合

Goal 的核心特色不是"记录一句话"，而是**让回合自己续下去**。

`runtime.rs` 在每个回合结束时检查当前 thread 的 goal 状态：

1. 如果 goal 是 `active`，且模型最后一回合**没说自己完成**：从
   `goal_templates::continuation_prompt()` 渲染一段"你还没说完，
   继续"的 user-role 消息，自动开下一回合。
2. 如果 `tokens_used >= token_budget` 且状态还是 `active`：
   `apply_token_increment` 自动把状态翻成 `budget_limited`，
   下一回合 user-side prompt 改成 `budget_limit.md` 模板（"你已经
   达到预算上限，整理一份 final summary 给我"）然后停。
3. 如果 `paused` / `complete` / `budget_limited`：完全不开新回合，
   等用户操作。

模板在 `omicos-core/templates/goals/{continuation,budget_limit}.md`
作为 `include_str!` 嵌入兜底。允许用户在
`<workspace>/.omicos/templates/goals/<name>.md` 覆盖（**仅工作区**，
不支持 `~/.omicos` 或环境变量覆盖——见
[Workspace = cwd](04-workspace-and-conversation.md)）。

```{admonition} 占位符
:class: tip

模板里支持的占位符：

`{{objective}}` `{{goal_id}}` `{{tokens_used}}` `{{token_budget}}`
`{{budget_suffix}}`（渲染成 `" / budget 500000"` 或
`" (no budget)"`）`{{elapsed}}`。
```

## token 计费

PR omicos-core #142 + #143 让 token 计费成为 goal 系统的**核心副作
用**——每个回合结束 sidecar 都会调一次：

```rust
goal.apply_token_increment(delta_in, delta_out);
```

`delta_*` 来自 provider 返回的 `usage` 块（OpenAI / DeepSeek /
Anthropic 都有）。这两个数字分别记到 `tokens_in_used` /
`tokens_out_used`，相加成 `tokens_used`。budget 阈值用的是
**总和**——但 UI 显示分两条（input 通常远大于 output，分开能让用户
看清"我大头花在装上下文还是产文本"）。

`apply_token_increment` 自带**单向 budget 翻转**：

- 只有 `active` 且 `tokens_used >= budget` 才翻成 `budget_limited`
- `paused` / `complete` 永远不被自动翻

## SPA UI 入口

omicOS-ui 把这套暴露成三个组件：

| 文件 | 角色 |
|---|---|
| `src/stores/goalStore.ts` | pinia store；订阅 active session，poll `GET /goal` |
| `src/components/chat/GoalPill.vue` | composer 上方的 pill —— 显示 objective、剩余预算、暂停按钮 |
| `src/components/chat/GoalStatusBar.vue` | composer 上方更细的 token bar：`129.0k (126.3k↓ / 2.7k↑) / 500k` |

`/goal` 在 composer 里是 slash command（`BenchView.vue` 拦截）：

| 写法 | 行为 |
|---|---|
| `/goal` | 打开 GoalPill，让用户在 UI 里输入 objective |
| `/goal <objective>` | 直接 `create_goal` + 把 objective 当 user-message 发出去触发第一轮 |
| `/goal pause` / `resume` / `complete` / `clear` | 走 PATCH |

```{admonition} 实时 token 显示
:class: note

`GoalStatusBar` 在 `isStreaming` 上升沿快照
`workspaceStore.currentUsage.input_tokens/output_tokens`，下降沿减一下
得到当前回合 delta；同时 `goalStore.refresh()` 拉服务端权威累加值。
两者交叉避免"流式中的数字跳跃"和"流式结束后才更新"之间的撕裂。
```

## 加一个自定义模板

最简单的"我想换措辞"方式：

```bash
mkdir -p <workspace>/.omicos/templates/goals
cat > <workspace>/.omicos/templates/goals/continuation.md <<'EOF'
You still have an active goal:

> {{objective}}

Used: {{tokens_used}}{{budget_suffix}}. Continue working — execute the
next concrete step. When the entire goal is done, call
`update_goal {complete: true}` and STOP.
EOF
```

下一回合自动走你的模板。`budget_limit.md` 同理。
**不在工作区路径下的模板不会被加载**。

## 故障排查

| 现象 | 排查 |
|---|---|
| `/goal foo` 没自动跑第一回合 | composer 拦截器没装好；看 `BenchView.vue` `/goal\s+(.+)/` 分支 |
| token bar 显示 `0` | provider 没 emit usage（部分 OAuth Gemini 不发）；只能依赖客户端估算（未实现） |
| budget 没生效，过了预算还在跑 | `apply_token_increment` 没在回合末调；grep `apply_token_increment` 看 runtime.rs 末尾 |
| status 永远是 `pending` | 模型回合里没调 `update_goal { complete: true }`，被 continuation engine 一直续；增大 prompt 里的"任务结束条件"指令 |

## 进一步

- [对话与工作区](04-workspace-and-conversation.md) — workspace 路径是 goal templates 的搜索根
- [Tool pipeline](../omicos-core/04-tool-pipeline.md) — `create_goal` / `get_goal` / `update_goal` 的注册位置
