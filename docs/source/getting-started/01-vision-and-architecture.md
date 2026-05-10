# 项目愿景与三层架构总览

OmicOS 的目标是把 LLM 能力**接到本地 Jupyter 内核之上**，给生信研究者
一个跨 omics 数据分析、文献追踪、复现/审稿的桌面 agent 工作台。整个系统
是个三层结构：

1. **Tauri 桌面前端** — 用户面对的 UI（Vue 3 SPA + Rust 容器）。
2. **Rust sidecar** — 每个 Tauri 进程拉起的本地 HTTP 服务，承担
   *agent 编排 + LLM 流式调用 + 工具执行 + 内核通信* 的全部脏活。
3. **Python kernel** — 一个独立的 IPython 内核进程，跑实际的
   `pandas` / `scanpy` / `omicverse` 代码。前端从来不直接和它说话。

外加一个**共享后端 admin 服务器**——发布并维护 agent 模板与 skill
playbook，所有桌面端启动时拉一份本地缓存。

```
┌───────────────────────────────────────────────────────────────┐
│                       用户的 Mac / PC                          │
│                                                               │
│   ┌──────────────┐    HTTP/SSE (loopback)    ┌──────────────┐ │
│   │ Tauri SPA    │ ◀──────────────────────▶ │ omicos-core  │ │
│   │ (Vue 3 + TS) │                          │ (Rust)       │ │
│   └──────────────┘                          │   sidecar    │ │
│                                             │              │ │
│                                             └──────┬───────┘ │
│                                              ZMQ ↕  IPython  │
│                                             ┌──────┴───────┐ │
│                                             │ omicos-env   │ │
│                                             │ (.venv)      │ │
│                                             │  Jupyter K   │ │
│                                             └──────────────┘ │
└────────────────────────┬──────────────────────────────────────┘
                         │ HTTPS (sync only, on startup
                         │  + on user "refresh" button)
                         ▼
            ┌──────────────────────────────┐
            │ omicos-admin (Flask)         │
            │   /var/omicos-admin/         │
            │     ├─ agents/<id>.md        │
            │     ├─ skills/<id>/SKILL.md  │
            │     └─ models.json           │
            └──────────────────────────────┘
```

## 三层之间的契约

每一层都有明确的 *输入边界* 和 *副作用边界*。当你想加新功能时，第一步是
确定它属于哪一层——选错层是工程债的最大来源。

### Tauri SPA（[omicOS-ui](https://github.com/PrimorDecode/omicos-ui)）

- **职责**：渲染对话、文件树、Notebook 单元；管理用户的本地工作区路径；
  配置 API key、模型、agent 选择；展示 skill / agent 卡片。
- **不做**：直接调用 LLM API；直接读写工作区文件（除了 Tauri 自带的
  开窗 / 文件选择器之类的 OS 交互）；直接和 Jupyter 内核说话。
- **状态**：Pinia stores + 少量 Tauri persisted state。每次启动重新从
  sidecar 拉数据，不在前端做长期持久化。

### Rust sidecar（[omicos-core](https://github.com/PrimorDecode/omicos-core)）

- **职责**：编排 agent 团队 / 调度 LLM provider / 执行工具调用 / 维护
  对话历史 / 桥接 Jupyter 内核 / 同步 admin。
- **不做**：渲染界面；直接被外部网络访问（只 listen 在 127.0.0.1）；
  写跨用户的全局状态。
- **进程模型**：每个 Tauri 实例都拉起一个新的 sidecar，监听本地随机
  端口。两个用户两个工作区互不干扰。

### Python 内核

- **职责**：执行 `run_python_code` / `notebook_run` 工具的代码；维护
  AnnData 等会话状态；返回图表与结果。
- **不做**：和外部网络说话（除非用户写的代码自己 `requests.get`）；
  执行 LLM 调用。
- **进程模型**：sidecar 启动时通过 `omicos-env/.venv/bin/python -m
  ipykernel_launcher` 拉起，独占工作区。

### omicos-admin（共享后端）

- **职责**：发布 agent prompt 模板与 skill playbook；模型 catalog
  （base URL、env var）。
- **不做**：执行任何用户代码；保管用户的 API key；触达个人对话历史。
- **接入方式**：客户端启动时 `GET /api/public/{agents,skills}/manifest`
  拉清单，按 hash 增量同步。客户端**永远是 admin 的只读消费者**。

## 数据流的两个典型回合

### 回合 1：用户发一条消息

1. SPA 把用户消息 + 选中的 agent id POST 到 sidecar `/api/chat/stream`。
2. sidecar 解析当前 active agent → 决定 toolsets + skill 白名单 → 构建
   system prompt → 调对应 provider 的流式接口（OpenAI / Gemini / 任意
   兼容 ChatCompletions 的服务）。
3. provider 边吐 token，sidecar 边把 token / tool call / SSE event
   推回 SPA。
4. SPA 渲染 token 到对话气泡里。
5. 如果 LLM 决定调工具：sidecar 截下 tool call，本地执行
   （`run_python_code` 走内核、`web_search` 走 Exa/DDG、`skill` 走
   playbook 加载……），把结果作为下一轮 prompt 的一部分喂回 LLM，循环
   直到模型给出最终答复。

### 回合 2：用户切到另一个 agent

1. SPA 调 `/api/agents` 列表 → 用户点了 `literature_scout`。
2. 选择只是改前端状态——不立即触发任何 sidecar 调用。
3. 下次发消息时，新的 agent id 进入 chat 请求；sidecar **重新构建
   system prompt**，用新 agent 的 toolsets 与 `skills:` 白名单替换旧的。

## 三个仓库的物理布局

在用户机器上：

```
~/Library/Application Support/com.omicverse.omicos/
└── workspace/                # 默认对话 / 设置存储
    ├── account.json          # plan_code、登录态
    ├── conversations/        # 历史对话（.json）
    └── settings/             # API key、provider 配置

~/.omicos/                    # 客户端只读缓存
├── cloud-skills/skills/      # 从 admin 同步的 skill 包
├── cloud-agents/agents/      # 从 admin 同步的 agent 模板
└── cloud-models/             # 从 admin 同步的模型清单

/Applications/OmicOS.app/Contents/
├── MacOS/
│   ├── omicos-desktop        # Tauri Rust 容器
│   └── omicos                # Rust sidecar 二进制
└── Resources/binaries/
    └── omicos-env/.venv/     # 内核 Python venv
```

服务器侧：

```
/var/omicos-admin/            # 数据目录（systemd 配置 OMICOS_ADMIN_DATA）
├── agents/<id>.md            # agent 模板
├── skills/<id>/SKILL.md      # skill playbook
└── models.json               # 模型 / provider catalog
```

## 接下来读什么

- [仓库分布与职责](02-repos-and-roles.md) — 一张表对照所有 git 仓库
- [本地开发环境搭建](03-dev-environment.md) — Rust + pnpm + Python 内核
- [Agent / Team / Toolset 模型](../concepts/01-agent-team-toolset.md) — 核心抽象
- [Skill 系统](../concepts/02-skills-system.md) — 发现、白名单、执行
