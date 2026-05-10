# Pinia stores

omicOS-ui 用 Pinia 做状态管理。state 不持久化（除少量 Tauri secure
storage 的 API key），每次启动都重新从 sidecar 拉。

## 主要 store 概览

| Store | 文件 | 用途 |
|---|---|---|
| `workspace` | `stores/workspaceStore.ts` | 当前 workspace、conversation 历史、流式状态 |
| `team` | `stores/teamStore.ts` | active agent、team members |
| `provider` | `stores/providerStore.ts` | 当前 model + provider 选择 |
| `settings` | `stores/settingsStore.ts` | API key、image host 配置 |
| `kernel` | `stores/kernelStore.ts` | 内核状态、变量列表 |
| `plan` | `stores/planStore.ts` | plan-mode 草稿 |

## workspaceStore — 最大的一个

负责对话历史 + 同步状态。关键 actions：

- `streamChat(content)` — fetch + ReadableStream → 派发 SSE event
- `syncNow()` — 拉 server 历史覆盖本地，**保留 client_only 尾部消息**
- `selectConversation(sid)` — 切到已有对话
- `newConversation()` — 开新对话

### `client_only` 保护

PR #108 修的 bug：`syncNow()` 之前会把流式错误覆盖掉。修复方案是
在 store 里给某些消息打 `client_only: true`，sync 完按这个 flag
重新追加。详见 [Workspace 与 Conversation](../concepts/04-workspace-and-conversation.md#client_only-字段)。

## 不在 store 里的状态

- 用户的 API key — Tauri secure storage / OS keychain
- 当前路由参数 — vue-router
- 一次性 flash message — `<Toast>` 组件 local state

## 反模式

避免：

- 在 store 里保存"上次拉到的 conversation"——每次都从 sidecar 拉
- 在 store 里持有大对象引用——把对象放 sidecar，store 只存 id
- 跨 store 的循环依赖——发现就拆抽离 helper

## 进一步

- [整体架构](01-architecture.md)
- [Sidecar 生命周期](02-sidecar-lifecycle.md)
