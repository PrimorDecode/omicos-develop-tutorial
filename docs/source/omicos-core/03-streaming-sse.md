# 流式推理与 SSE

`POST /api/chat/stream` 返回的是 Server-Sent Events 流。SPA 用
EventSource / fetch+stream-reader 消费，按 event 类型派发到 store。

## 事件类型

| Event | Data shape | 用途 |
|---|---|---|
| `message_start` | `{role, ...}` | 一段 assistant 消息开始 |
| `chunk` | `{delta: "..."}` | 增量 token |
| `tool_call_start` | `{id, name}` | LLM 决定调工具 |
| `tool_call_args_delta` | `{id, delta}` | 工具参数增量 |
| `tool_call_end` | `{id, args}` | 工具参数完整 |
| `tool_result` | `{id, name, status, result}` | 工具执行结果 |
| `message_end` | `{usage}` | 一段消息结束（含 token usage） |
| `agent_switch` | `{from, to}` | call_agent 切了 agent |
| `error` | `{message, kind}` | 错误（不一定致命） |
| `done` | `{}` | 整个 turn 结束 |

## 同步消息 vs 流

每个 SSE event 都对应 `messages: []` 历史里的一个或多个条目变化。
当流结束（`done` event），sidecar 会 `store.append(...)` 把完整的
assistant + tool messages 持久化到 `conversations/<sid>.json`。

```{admonition} client_only 消息
:class: note

某些消息（例如 stream 中断的错误提示）只该出现在客户端、不发回 LLM。
SPA 标 `client_only: true`，server-side sync 时保留。
详见 [Workspace 与 Conversation](../concepts/04-workspace-and-conversation.md#client_only-字段)。
```

## 中断 / 重连

- SPA 主动中断：直接关 EventSource，sidecar 检测到客户端断开会停止
  生成（不重启进程）
- 网络断：sidecar 继续跑、消息照样持久化到磁盘——SPA 重连后从
  `/api/conversations/:sid` 拉就行

## 进一步

- [Tool execution pipeline](04-tool-pipeline.md) — tool_result 怎么生成
- [HTTP API](02-http-api.md) — endpoint 全景
