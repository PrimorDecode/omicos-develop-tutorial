# 错误处理与自恢复

sidecar 是一个"长跑"进程，掉一次就让用户体验断流。omicos-core 在
错误处理上有几条**铁律**，写新代码时必须遵守。

## 铁律 1：工具 `Err` 不杀 turn

任何工具内部 `Err(...)` / `bail!()` 都会被 `ToolExecutor::run` 末尾
统一捕捉，转成 `{"status": "error", "result": "<message>"}` 塞给
LLM。LLM 拿到错误信息自己决定下一步——可能换个参数重试，也可能
告诉用户。turn 不会因此中断。

```rust
// 这是 ToolExecutor::run 末尾的 finalizer
let (status, text) = match result {
    Ok(value) => ("done", stringify_tool_result(&value)),
    Err(err) => ("error", err.to_string()),
};
```

**不要**自作主张在工具内部 `process::exit` 或 panic，那才是真的杀
turn。

## 铁律 2：网络 / IO 错误必带 context

用 `anyhow::Context::context()`，告诉调用者**做什么时候**失败的：

```rust
client.get(&url).send().await
    .with_context(|| format!("GET {url}"))?
    .error_for_status()
    .with_context(|| format!("non-200 from {url}"))?
```

错误日志能定位到具体 URL，而不是"reqwest error: connection refused"
这种废话。

## 铁律 3：致命错误 → 分类 + emit event

某些错误是 sidecar 真的没法继续的——workspace 锁冲突、读写权限丢失、
端口被占。这种情况：

1. 写完整的 stderr 到日志
2. 分类成 `kernel_fatal_error.kind`：`workspace_conflict` /
   `read_only_workspace` / `port_conflict` / `unknown`
3. 通过 Tauri event API emit `kernel-fatal-error` 给 SPA
4. 进程退出（不要无限重试）

SPA 弹原生 `confirm()`，让用户决定是否重启。重启走
`POST /api/restart_backend`。源码：[`omicos-ui/src-tauri/src/lib.rs`](https://github.com/PrimorDecode/omicos-ui/blob/main/src-tauri/src/lib.rs)
的 fatal-error classifier。

## 铁律 4：流式管道断开静默降级

SSE 接收方关闭（用户切走 / 网络断 / SPA 崩）→ sidecar **继续完成
当前 turn**，结果落 conversation store。下次用户回来
`GET /api/conversations/:sid` 还能读到。

具体看 `runtime::emit()`——失败的 send 用 `OnceLock` 控制
"per-process 只 warn 一次"，避免日志洪水。

## 铁律 5：永远不暴露 secrets 到日志

API key / OAuth token / refresh token 必须在打印前 mask。
`tracing::debug!(key = "<redacted>", ...)` 而不是
`tracing::debug!(key = %real_key, ...)`。

## 自恢复列表

omicos-core 主动恢复的错误场景：

| 场景 | 恢复策略 |
|---|---|
| Sync admin 网络断 | 跳过本次 sync，下一回合再试 |
| Sync admin 返回 `AppendOutcome::Permanent`（4xx schema 错） | 游标推进到这批末尾，跳过坏 batch（PR #131） |
| 内核 ZMQ heartbeat 丢失 | 重启内核子进程，标记当前 conversation 状态 |
| **kernel worker stdin EPIPE** | 等同 stdout EOF，触发 respawn（PR #137） |
| Provider 5xx | 当前 turn 失败 + 报错给 LLM/SPA，不重试（避免账单） |
| Provider 429 | 同上 + 在错误信息里提示用户切模型 |
| Tauri 主窗口外的子窗关闭 | 不杀 sidecar（PR #105） |
| sidecar 异常退出 | Tauri 容器 800ms 退避后重启，最多 N 次 |

## context-overflow 400 与 kernel 失败要分开

PR omicos-core #133 修了一个长期 bug：**模型返回 400 context-length
exceeded** 跟**内核挂掉**走的是同一个错误路径——SPA 都弹"内核异常，
是否重启"，让用户重启了没用的子进程。

现在 `runtime` 在解析 provider 400 时优先检查 message body 是否含
`context_length_exceeded` / `maximum context` / `too long` 等 marker：

- 是 → emit `context_overflow` 事件，SPA 弹"对话太长，建议 compact 或新开"
- 否 → 走原 `kernel_fatal_error` / `provider_error` 路径

写新的 provider 集成时，对应的 400 解析也要走这层 classifier
（`runtime::classify_provider_400`），不然就走兜底 = 误报 kernel 死。

## 进一步

- [启动与生命周期](01-startup-lifecycle.md) — restart 流程
- [Tool pipeline](04-tool-pipeline.md) — tool 错误的统一格式
