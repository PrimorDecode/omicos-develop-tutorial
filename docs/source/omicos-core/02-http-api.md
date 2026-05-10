# HTTP API 全景

sidecar 用 axum 暴露 REST + SSE 接口。所有 endpoint 都监听
`127.0.0.1:<random-port>`，端口写在 `<workspace>/.omicos/serve.pid`。

源码 single source of truth：[`server.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/server.rs)
开头的 `Router` 注册块。

## Endpoint 速查

### 对话流

| Method | Path | 用途 |
|---|---|---|
| `POST` | `/api/chat/stream` | SSE 流式 chat，主入口 |
| `GET` | `/api/conversations` | 列出所有对话 |
| `GET` | `/api/conversations/:sid` | 单条对话历史 |
| `DELETE` | `/api/conversations/:sid` | 删除对话 |

### Agent / Skill catalog

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/api/agents` | 列出 agent + 当前 team |
| `GET` | `/api/agents/:id/tools` | 单个 agent 解析后的工具 schema |
| `POST` | `/api/agents/refresh` | 强制 sync admin |
| `GET` | `/api/skills` | 列出 skill 卡片（SPA 用） |
| `POST` | `/api/skills/refresh` | 强制 sync admin |

### Provider / 设置

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/api/providers` | 可用 model provider |
| `POST` | `/api/settings/api-keys` | 写 API key（落 keychain） |
| `GET` | `/api/settings` | 读全部设置 |

### Workspace / Notebook

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/api/workspace` | 当前 workspace 路径 |
| `POST` | `/api/workspace/switch` | 切到新工作区（重启自身） |
| `GET` | `/api/notebook` | 当前 notebook 状态 |
| `POST` | `/api/notebook/run` | 执行单元格 |

### 系统

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/api/stats` | 当前 turn 的 token 预算估算 |
| `GET` | `/api/health` | 健康检查 |
| `POST` | `/api/restart_backend` | 重启 sidecar |

## 设计约定

- **永远 loopback only**：`bind 127.0.0.1`，绝不暴露到公网
- **JSON 输入输出**（除 SSE）
- **SSE 用 `text/event-stream`**，格式：`event: <type>\ndata: <json>\n\n`
- **错误**：`{"error": "...", "kind": "..."}` 的 4xx / 5xx
- **认证**：进程级，sidecar 假定调用方就是同机用户。**不做 token 校验**
  ——它只该被同机的 Tauri SPA 调用

## 加新 endpoint

在 `server.rs` 的 `Router::new()` 里挂一行 `.route(...)` + 写
对应 handler。约定上每个 endpoint 都写 doc comment 说明用途和 caller，
便于 grep。

## 进一步

- [Tool execution pipeline](04-tool-pipeline.md) — chat/stream 内部的工具循环
- [Streaming SSE](03-streaming-sse.md) — chat/stream 的事件细节
