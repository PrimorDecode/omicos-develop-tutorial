# 公开 API 与缓存机制

admin 的 `/api/public/*` endpoint **完全无鉴权**——agent prompt 是
公共产品内容（任何用户都能看到）。如果以后要做 Pro-tier gating，门
应该开在 omicos-server / omicos-core 一侧（校验 plan_code），而不是
admin。

## Endpoint 清单

### Agent

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/api/public/agents` | 完整 list（含 body） |
| `GET` | `/api/public/agents/manifest` | 轻量清单 `{id, hash, tier, updated_at}` |
| `GET` | `/api/public/agents/<id>` | 单个 detail |

### Skill

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/api/public/skills` | 完整 list（含 body） |
| `GET` | `/api/public/skills/manifest` | 轻量清单 |
| `GET` | `/api/public/skills/<id>` | 单个 detail |

### Models

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/api/public/models` | 完整 catalog |
| `GET` | `/api/public/models/manifest` | 轻量清单（version + hash） |

## 增量同步协议

客户端流程（[`cloud_skills.rs::sync_once`](https://github.com/PrimorDecode/omicos-core/blob/main/src/cloud_skills.rs)）：

1. `GET /manifest` → 拿到当前 `version` + 所有 entry `hash`
2. 对比本地 `manifest.json`，找出 hash 变化的 id
3. 改动的 → `GET /<id>` 拉详情 → `atomic_write` 落盘
4. server 不再有的 entry → 本地删（GC）
5. 写新 `version` 到本地 manifest

```{admonition} hash 怎么算
:class: note

Python 端：`hashlib.blake2b(<file_bytes>, digest_size=8).hexdigest()` —
8 字节 hex（16 字符）。文件二进制改一字节就变。
```

## Frontmatter projection

admin 在返回 JSON 时只把 frontmatter 里的特定 key 投影出来。
[`app.py`](https://github.com/PrimorDecode/omicos-admin/blob/main/app.py)：

```python
_PROJECTED_KEYS = (
    "id", "name", "description", "icon",
    "tier", "version", "toolsets", "skills",
)
```

加了未识别的 frontmatter 字段，admin 会忽略——这是兼容性策略，让
将来加新字段不破坏老客户端。

## CORS

admin 默认开 `*` CORS——任何域都能 GET。同样基于 "agent prompt 是
公共产品内容" 的判断。如果你要对接私有部署，在反向代理层做 CORS
收紧。

## Rate limiting

目前**无**。流量靠反向代理 / CDN 处理。预期 QPS 不高（每个客户端
启动 sync 一次 + 用户偶尔点"刷新"）。

## 进一步

- [鉴权](03-auth.md) — admin 写接口 / panel 鉴权
- [部署](04-deployment.md)
