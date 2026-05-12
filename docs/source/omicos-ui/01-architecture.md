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
- `/agents` — agent 卡片（2026-05 起按 category 分行，每行水平滚动）
- `/skills` — skill 卡片（同 Agent 一套布局——每分类一行 + SVG 图标）
- `/notebook` — 内核 / notebook
- `/files` — workspace 文件树（HTML 在沙箱 iframe 渲染、Markdown 默认渲染 + 可切原文）
- `/settings` — API key、provider（含"在 picker 显示"逐 provider 开关）、image-host

## 几个 2026-05 的关键交互组件

- **GoalPill** + **GoalStatusBar** — composer 上方的长时程任务条；
  `/goal <objective>` 一行直接启动。详见 [Goal 模式](../concepts/06-goal-mode.md)。
- **PermissionPill** + **ToolApprovalCard** + **FullAccessConfirmDialog** —
  codex-style 三档权限。详见 [权限模式](../concepts/07-permission-mode.md)。
- **Agent 卡片新版** — 7 个 SVG 图标按 category 替换 emoji、中文 summary
  + use_when + example_prompts 直接显示。PR omicOS-ui #111-#115。
- **Notebook 4 bugs 修复合集**（PR #127） — 重命名 EINVAL、磁盘同步、
  执行计数器重置。
- **Markdown 文件预览** — 默认渲染、可切原文；HTML 文件用沙箱 iframe 加载，
  同 workspace 的 CSS / JS / 图片自动 inline（PR #116、#117、#130、#132）。

## 不在前端做的事

- **不直接调 LLM**——所有 chat 走 sidecar
- **不做长期持久化**——除少量 Tauri secure storage（API key）
- **不缓存 conversation**——每次 reload 都从 sidecar 重新拉

## 进一步

- [Sidecar 生命周期](02-sidecar-lifecycle.md)
- [Pinia stores](03-stores.md)
- [编译与打包](04-build-and-bundle.md)
