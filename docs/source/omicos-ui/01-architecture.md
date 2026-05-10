# Vue 3 + Tauri 整体架构

omicOS-ui 是一个 Tauri 2 桌面 app：内核是 Rust 写的窗口容器，UI 部分
是 Vue 3 + TypeScript SPA。

## 组件分层

```
┌────────────────────────────────────────┐
│ Vue 3 SPA (TypeScript, in WebView)     │
│   ├─ vue-router                        │
│   ├─ Pinia stores                      │
│   ├─ DOMPurify-safe markdown renderer  │
│   └─ axios + EventSource → sidecar     │
└──────────────────┬─────────────────────┘
                   │ Tauri IPC + plain HTTP/SSE (loopback)
                   ▼
┌────────────────────────────────────────┐
│ Tauri Rust shell (src-tauri/src/)      │
│   ├─ sidecar lifecycle                 │
│   ├─ window event hooks                │
│   ├─ tauri-plugin-shell                │
│   └─ auto_key_* commands               │
└──────────────────┬─────────────────────┘
                   │ stdout pipe + child events
                   ▼
                 omicos sidecar
```

## SPA 入口

`src/main.ts`：

- 装 Vue + vue-router + pinia
- 挂全局 click 拦截（外链走 OS 浏览器，PR #107）
- 挂 `kernel-fatal-error` listener
- 进 `<router-view>` 渲染

## 路由

主要 route：

- `/` — 主对话页
- `/agents` — agent 卡片
- `/skills` — skill 卡片
- `/notebook` — 内核 / notebook
- `/files` — workspace 文件树
- `/settings` — API key、provider、image-host

## 不在前端做的事

- **不直接调 LLM**——所有 chat 走 sidecar
- **不做长期持久化**——除少量 Tauri secure storage（API key）
- **不缓存 conversation**——每次 reload 都从 sidecar 重新拉

## 进一步

- [Sidecar 生命周期](02-sidecar-lifecycle.md)
- [Pinia stores](03-stores.md)
- [编译与打包](04-build-and-bundle.md)
