# 权限模式（codex-style）

2026-05 之前，OmicOS 用两个布尔 `allow_shell` / `allow_file_write`
表达"用户允许做这些事吗"。PR omicos-core #127 + omicOS-ui #125
把它升级成 codex / claude code 的**三档权限模式**：

| 模式 | shell | file_write | python | 风险工具是否要求逐次批准？ |
|---|---|---|---|---|
| `read_only` | ❌ | ❌ | ❌ | — 工具直接从 schema 隐藏 |
| `auto` | ✓ | ✓ | ✓ | ✓ — 每次调用都要用户批准 |
| `full` | ✓ | ✓ | ✓ | ❌ — 一律放行 |

源码：
[`omicos-core/src/approvals.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/approvals.rs)
+ `protocol.rs::PermissionMode` + `runtime.rs::maybe_gate_tool_call`。

## ToolRisk 分类

工具按"做了什么"分四类：

```rust
pub enum ToolRisk {
    Read,        // file_manager__read / glob / grep / list / ... — 无副作用
    FileWrite,   // file_manager__write / edit / notebook_edit
    Python,      // run_python_code / kernel_install
    Shell,       // shell
}
```

`tool_risk(name)` 是个 match。`Read` 是兜底——任何没被显式标记的工具
都按"只读"对待。

## 三档模式的语义差

**`read_only`**：sidecar 在构建 LLM 看到的 `tools[]` schema 时**直接
过滤掉** `FileWrite` / `Python` / `Shell` 三类工具——LLM 根本不知道它
们存在，也就不会去调。

**`auto`**：所有工具暴露给 LLM，但 `FileWrite` / `Python` / `Shell`
被调用时 sidecar 不立刻执行，而是 emit 一个 `ToolApprovalRequest`
事件给 SPA，挂起等用户决定。SPA 弹一张 ApprovalCard，三个按钮：

- **Allow once** — 只放行这一次
- **Allow for session** — 这条会话内 *同名工具* 一律放行
- **Deny** — 拒绝，模型收到 `{"status": "error", "result": "denied by user"}`

"session 放行"由 `ApprovalCenter::mark_session_allowed` 持久化，
key 是 `(session_id, tool_name)`。换 session 就重新问一次。

**`full`**：跳过整个 gate，等价于过去的 `allow_shell=true,
allow_file_write=true`。

## wire 协议

ChatConfig 里现在带 `permission_mode` 字段：

```text
{
  "session_id": "...",
  "messages": [...],
  "permission_mode": "auto",
  // 兼容性：老客户端的 allow_shell / allow_file_write 仍被识别
  //         如果两套都传，老字段优先（PR #127 的兼容策略）
}
```

`PermissionMode::from_str` 接受这些别名：

| 输入 | 解析为 |
|---|---|
| `read_only` / `readonly` / `read-only` | `ReadOnly` |
| `auto` | `Auto` |
| `full` / `full_access` / `full-access` | `Full` |
| 缺失 / 未识别 | `Full`（向后兼容） |

```{admonition} 默认值的取舍
:class: warning

sidecar 端默认 `Full`（让没改代码的老客户端继续工作）。
**SPA 端默认 `read_only`**（让首次使用的用户最安全）。两者不冲突——
SPA 默认会显式发 `permission_mode: "read_only"`，sidecar 的 `Full`
兜底只用于真的没传字段的客户端（CLI / 第三方集成）。
```

## 事件协议

```text
// 事件 1：sidecar 暂停在某个工具，等批准
{
  "type": "tool_approval_request",
  "call_id": "call_abc",
  "tool_name": "run_python_code",
  "risk": "python",
  "summary": "Execute: adata = sc.read_h5ad('/data/big.h5ad') ...",
  "arguments": { ... },
  "execution_context_id": "main" // call_agent 子回合会换 id
}

// 事件 2：SPA 应答（POST /api/tool-approval/{session_id}/{call_id}）
{
  "decision": "allow_session"   // 别名：allow / ok / approve → allow_once
                                //      session / always → allow_session
                                //      reject / cancel → deny
}

// 事件 3：sidecar emit 决议（trajectory 日志用）
{
  "type": "tool_approval_resolved",
  "call_id": "call_abc",
  "decision": "allow_session",
  ...
}
```

## SPA 实现要点

`src/stores/permissionStore.ts`：

- 状态持久化到 `localStorage["omicos.permission_mode"]`
- 默认 `read_only`
- 切到 `full` 时强制弹 `FullAccessConfirmDialog.vue` 让用户二次确认
  （"是的，我知道这意味着 sidecar 会自动跑 shell"），不能一键过

`ToolApprovalCard.vue` 是一张 chat 里 inline 的卡片，跟 LLM tool
call streaming 同节奏。Approved 之后变 collapsed 摘要；Denied 之后
显示 "❌ Denied by you"。

## 跟历史 toolchecker 的关系

老的 `allow_shell` / `allow_file_write` 是**整个 session 一刀切**的
开关——开了就一直开。新模式是**逐次问** + **按工具记忆**。两者
关系：

- sidecar 同时接受新老字段；老字段 *优先* 当兜底（保证老 CLI 不破）
- 新字段 `read_only` ⇔ 老的 `allow_shell=false, allow_file_write=false`
  + python 也禁
- 新字段 `full` ⇔ 老的 `allow_shell=true, allow_file_write=true`
- 新字段 `auto` 没有等价老语义，是这一版加进来的

## 进一步

- [Tool pipeline](../omicos-core/04-tool-pipeline.md) — `maybe_gate_tool_call` 在 ToolExecutor 之前
- [omicOS-ui 架构](../omicos-ui/01-architecture.md) — Permission Pill 在哪
