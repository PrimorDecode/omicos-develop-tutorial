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

## 不参与 cloud sync 的资源

以下资源**只在本地**，不与 admin 同步：

- 用户的 conversation 历史
- 用户的 API key（settings）
- workspace 文件
- trajectories
- memory（per-conversation 的）

这些都是隐私敏感数据——admin 端从设计上就不持有，避免承载用户数据
的法律 / 合规负担。

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
