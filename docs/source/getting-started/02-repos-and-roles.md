# 仓库分布与职责

OmicOS 的代码不在一个 monorepo——拆成多个仓库，每个负责一层。下表是
你贡献代码前应该知道的全景：

| 仓库 | 角色 | 主要语言 | 入口 |
|---|---|---|---|
| [PrimorDecode/omicos-core](https://github.com/PrimorDecode/omicos-core) | Rust sidecar — agent 编排、LLM 流式、工具执行、内核桥接 | Rust 1.78+ | `src/main.rs` → `src/server.rs` |
| [PrimorDecode/omicos-ui](https://github.com/PrimorDecode/omicos-ui) | Tauri 桌面前端 — Vue 3 SPA | Vue 3 + TS + Rust（Tauri 容器） | `src/main.ts` |
| omicos-admin | Flask 共享后端 — agent / skill / model catalog | Python 3.11 (Flask + Gunicorn) | `app.py` |
| omicos-env | 内核 venv — `omicverse` 等科学栈打包 | Python 3.11 | `pyproject.toml` |
| [PrimorDecode/omicverse-tutorials](https://github.com/PrimorDecode/omicverse-tutorials) | 用户向教程（Jupyter notebooks） | Python | — |
| **本仓库** | 开发者文档（你正在读） | Markdown / Sphinx | `docs/source/index.md` |

## 谁依赖谁

```
              ┌─────────────────────┐
              │  omicos-admin       │
              │  (单独部署)         │
              └──────────┬──────────┘
                         │ HTTPS sync only
                         ▼
┌──────────┐  spawn  ┌───────────────┐  spawn  ┌───────────┐
│ omicos-ui│ ───────▶│  omicos-core  │ ───────▶│ omicos-env│
│ (Tauri)  │         │  (Rust)       │   ZMQ   │ (Jupyter) │
└──────────┘         └───────────────┘         └───────────┘
```

- `omicos-ui` **依赖** `omicos-core` 二进制——构建 Tauri 包之前必须
  把 `omicos-core` 的 release sidecar 拷到
  `omicos-ui/src-tauri/binaries/omicos-aarch64-apple-darwin`（或对应
  平台名）。
- `omicos-core` **不依赖** `omicos-ui`——可以单独跑 `cargo run` 启动
  HTTP server，CLI 也用得着。
- `omicos-admin` **谁都不依赖**——是个孤立服务，对其它仓库零硬连接。

## 在本机的物理对应

```
~/Desktop/analysis/omicverse-project/
├── omicos-core/         # → PrimorDecode/omicos-core
├── omicOS-ui/           # → PrimorDecode/omicos-ui
├── omicos-admin/        # → 内部仓库
├── omicos-env/          # → 内核 venv（pyproject）
├── omicverse-skills/    # → 内置 skill 源（已弃用为 root，但仍是
│                        #    skill 写作的协作仓库）
└── omicos-develop-tutorial/   # ← 你正在读的
```

## 读源码的入口

写代码之前最该读的几个文件：

| 模块 | 关键文件 | 为什么重要 |
|---|---|---|
| omicos-core | `src/server.rs` | 所有 HTTP 路由都在这里登记 |
| omicos-core | `src/agents.rs` | `AgentSpec` + `TemplateStore` |
| omicos-core | `src/skills/mod.rs` | `SkillCatalog::discover` + filter |
| omicos-core | `src/runtime.rs` | turn 主循环：build prompt → call provider → 循环工具 |
| omicos-core | `src/tool_providers/mod.rs` | toolset 展开规则 |
| omicos-core | `src/providers.rs` | 3 个 provider 协议（ChatCompletions / Codex / Gemini） |
| omicos-ui | `src/stores/workspaceStore.ts` | conversation + sync 状态 |
| omicos-ui | `src-tauri/src/lib.rs` | sidecar 拉起 / 死亡处理 |
| omicos-admin | `app.py` | 全部 endpoint + 权限 |

## 进一步

- [本地开发环境搭建](03-dev-environment.md) — 把这几个仓库都 clone 下来
- [第一次构建](04-first-build.md) — sidecar + 桌面端联编
