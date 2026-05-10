# Workspace 与 Conversation

OmicOS 不是云端 SaaS——所有的"对话状态"都落在用户本地磁盘。
理解 workspace / conversation 的存储结构对调试持久化、迁移用户数据、
写新功能都关键。

## Workspace 概念

一个 **workspace** = sidecar 启动时绑定的工作目录。Tauri 桌面端在
首次启动时挑一个：

- 默认：`~/Library/Application Support/com.omicverse.omicos/workspace/`（macOS）
- 用户在"打开工作区"对话框选别的目录后，新进程会以那个目录为 workspace

workspace 是 sidecar 的进程级常量——`ToolExecutor::new(workspace, ...)`
启动时确定，整个生命周期不变。换 workspace = 重启 sidecar。

## Workspace 内的子目录

```
<workspace>/
├── .omicos/                 # 隐藏控制目录
│   ├── serve.pid            # sidecar 当前 PID + 端口
│   ├── trajectories/        # 完整 tool call 历史（JSONL）
│   ├── conversations/       # 对话历史 JSON
│   ├── plans/               # plan-mode 的草稿
│   └── outputs/<session>/   # 单次对话的图片 / .h5ad / .csv
├── agents/                  # （lab+）工作区本地 agent overlay
├── skills/                  # （lab+）工作区本地 skill overlay
└── <用户文件>               # 任意用户数据
```

```{admonition} cwd 即 workspace（设计决策）
:class: note

`.omicos` 默认是 cwd 相对的 ——这是有意为之，让用户在不同目录跑就能
得到不同 workspace。意味着**每次重启 OmicOS 必须从用户最初启动的
目录起**，否则会跌进新的空 workspace。
```

## Conversation

**Conversation** = 用户和 LLM 的一段对话。每条 conversation 是一个
JSON 文件（`.omicos/conversations/<session_id>.json`），shape（用 `…`
表示省略部分）：

```text
{
  "session_id":   "<uuid>",
  "agent_id":     "literature_scout",
  "team_members": ["omicverse_omni", "literature_scout"],
  "messages": [
    {"role": "user",      "content": "…", "ts": "…"},
    {"role": "assistant", "content": "…", "tool_calls": [ … ]},
    {"role": "tool",      "tool_call_id": "…", "content": "…"}
  ],
  "client_only": [ … ]
}
```

`messages` 数组直接是 OpenAI 兼容的 chat history shape，sidecar 在
每次新 turn 时用它构造下一次请求的 `messages: [...]`。

## `client_only` 字段

某些消息只该出现在客户端、不该被发回 LLM——典型场景是流式错误提示
（"网络中断"等）。这些用 `client_only: true` 标记，
[`syncNow()`](https://github.com/PrimorDecode/omicos-ui/blob/main/src/stores/workspaceStore.ts) 在用 server 历史覆盖本地时**保留**这些尾部 client-only 消息，
避免错误提示一闪而过（PR #108 修的 bug）。

## 进一步

- [Cloud sync](05-cloud-sync.md) — 同步 admin 资源到本地缓存
- [omicos-core 启动 / 生命周期](../omicos-core/01-startup-lifecycle.md) — sidecar 怎么找到这些目录
