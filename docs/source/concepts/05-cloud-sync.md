# Cloud sync — admin → 客户端缓存

omicos-admin 是 agent / skill / model catalog 的**唯一权威**。客户端
启动时拉一份本地缓存。本章讲同步协议、缓存格式、何时触发、怎么调试。

## 三类资源

| 资源 | 公开端点 | 客户端缓存路径 | 客户端代码 |
|---|---|---|---|
| Agent | `/api/public/agents` | `~/.omicos/cloud-agents/agents/<id>.md` | `cloud_agents.rs` |
| Skill | `/api/public/skills` | `~/.omicos/cloud-skills/skills/<id>/SKILL.md` | `cloud_skills.rs` |
| Model | `/api/public/models` | `~/.omicos/cloud-models/models.json` | `cloud_models.rs` |

## 同步协议（增量 + hash）

每个资源都遵循同一套设计：

1. `GET /<resource>/manifest` → `{[{id, hash, tier, updated_at}], version}`
2. 客户端读本地 `manifest.json`，对比每个 entry 的 hash
3. 改动的 → `GET /<resource>/<id>` 拉详情 → `atomic_write` 落盘
4. 不在 server manifest 里的本地 entry → GC 删除
5. 把 server `version` 写到本地 `manifest.json`

关键不变量：**单条 entry 的失败不影响其它 entry**。一个 skill 拉失
败只会 log warn，下一次同步会重试；不会让整个 sync 阶段崩溃。

## 触发时机

| 时机 | 触发方 |
|---|---|
| sidecar 启动后第一次 chat 之前 | 自动后台触发 |
| SPA 点"刷新"按钮 | `POST /api/agents/refresh` 或 `/api/skills/refresh` |
| `omicos cli sync` 命令 | CLI 显式触发 |

```{admonition} OFFLINE 模式
:class: note

设 `OMICOS_AGENTS_OFFLINE=1` 等环境变量可以禁用 sync——本地缓存
不被 GC，但也不会更新。CI / 离线演示用。
```

## 缓存目录可定制

| 资源 | 默认 | 覆盖变量 |
|---|---|---|
| agents | `~/.omicos/cloud-agents` | `OMICOS_AGENTS_CACHE_DIR` |
| skills | `~/.omicos/cloud-skills` | `OMICOS_SKILLS_CACHE_DIR` |
| models | `~/.omicos/cloud-models` | `OMICOS_MODELS_CACHE_DIR` |

或一次性：`OMICOS_LOCAL_HOME=/path/to/.omicos` 把整个家目录改写。

## 不参与 admin cloud sync 的资源

以下资源**不走 admin**，不参与上面的 `~/.omicos/cloud-*` 同步：

- 用户的 API key（settings）
- workspace 文件
- memory（per-conversation 的）

admin 端从设计上不持有它们，避免承载用户数据的法律 / 合规负担。

## conversation 与 trajectory：另一条同步轨道（omicOS-server）

conversation 历史和 trajectory 摘要**不**通过 admin 同步，它们走的是
**omicOS-server**——也就是 `auth.omicverse.com` 后端，是另一套服务。
这条轨道用来支持：

- 多设备查看自己的对话历史（桌面、iPad、手机 SPA）
- 实验室成员之间共享 trajectory
- 老师 / mentor 查看 lab 成员的工作

```{admonition} 两条 sync 轨道别混
:class: warning

| 资源 | 服务端 | 客户端入口 |
|---|---|---|
| agent / skill / model catalog | omicos-admin | `cloud_agents.rs` / `cloud_skills.rs` / `cloud_models.rs` |
| conversation 历史 + trajectory + group / lab | omicOS-server | `cloud_sync_conversations.rs` + 移动 SPA |

admin 只有"公共内容"，omicOS-server 有"用户内容"。
```

### 增量游标（2026-05 起）

PR omicOS-server #60 把 conversation 同步从"每次 poll 拉全部"换成
游标增量：

- `GET /api/processes/{pid}/conversations/{sid}?since_seq=N` 只返回
  `history[N:]`；空数组说明客户端已经追上。
- 客户端 IndexedDB 在 `_IDB_STORE_CONV` 里持久化每条会话的 `last_seq`，
  重连 / 重启后从这个游标恢复。

### WebSocket push（取代 polling）

`/ws/events` 是**每用户**一条长连接（PR omicOS-server #60），sidecar /
SPA 订阅后由服务器主动推：

- `process_updated` —— 哪一条 conversation 又出新消息
- `trajectory_summary_pending` / `trajectory_summary_ready` —— LLM 摘要状态
- `discussion_new` —— 别人在你的 trajectory 下留言

```{admonition} reconnect 模型
:class: tip

WS 不可靠。客户端断线重连后总是走一遍 REST `?since_seq=<last_seq>`
catch-up，再切回 WS push。WS 只负责"push 提示"，REST 才是真实数据
源。这套思路在移动 SPA `omicos-server-ui` 里实现得最完整。
```

### Trajectory Q&A：另一种交互（PR #63、#65）

trajectory 不再是只读的 summary。viewer 可以对一条 trajectory 发起
chat：

- `POST /api/trajectories/{sid}/discuss` —— body 是 `messages: [...]`
  滚动 chat；返回 `{reply, model}`。LLM 阅读这条 trajectory 的缓存
  summary + 用户的问题，给出回答。
- `GET /api/trajectories/{sid}/discussions` —— owner-only。返回**谁**
  对自己这条 trajectory 提过问、提了什么。

服务端把 viewer 的提问 + LLM 回答都持久化（owner 自己提问的不算
"discussion"，不入审计）。`GET /api/trajectories` 顺手暴露
`last_discussion_at` 给 owner，做未读小红点。

### 异步 summary refresh（PR #62）

`POST /api/trajectories/{sid}/summary/refresh` 在 2026-05 之前是同步的，
等 LLM 走完才返回。现在改成立即返回 `{enabled: true, status: "pending"}`
然后 `asyncio.create_task` 跑 LLM。SPA 通过 WS `trajectory_summary_ready`
或者 poll 拿最终结果。

### Capacitor / Ionic CORS（PR #61）

`capacitor://localhost`、`ionic://localhost`、`https://localhost` 现在
都在 CORS 白名单里——这是 iOS / Android Capacitor 壳子的来源 origin。
桌面 Tauri 也走 `https://localhost`（或 `http://127.0.0.1`），不受
影响。

### Lab 可见性放宽（PR #64-67）

`is_mentor_of` / `visible_session_owners` / lab members 可见性都做了
放宽——**any active member sees lab-mates**。背景：在多人 lab 里，
学生原本看不到师兄师姐的 trajectory（因为旧规则要求 `role = "mentor"`），
现在只要"在同一个 active lab"就够。详见
[omicOS-server / 数据布局](../omicos-admin/01-data-layout.md)（trajectory
权限段落）。

## 调试同步

```bash
# 看本地 manifest
cat ~/.omicos/cloud-agents/manifest.json | python3 -m json.tool

# 强制清空 + 重 sync
rm -rf ~/.omicos/cloud-skills && \
    curl -X POST http://127.0.0.1:<sidecar-port>/api/skills/refresh

# 直接看 admin 端
curl https://<admin-host>/api/public/skills/manifest | python3 -m json.tool
```

## 进一步

- [omicos-admin / 公开 API](../omicos-admin/02-public-api.md)
- [omicos-admin / 数据布局](../omicos-admin/01-data-layout.md)
