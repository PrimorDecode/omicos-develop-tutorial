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
| `GET` | `/api/public/skills/<id>` | 单个 detail（仅 `SKILL.md`，附 `file_count`） |
| `GET` | `/api/public/skills/<id>?include_files=1` | 完整目录树（含 reference.md / 模板等） |

#### `?include_files=1` 详解（PR #13）

```json
{
  "id": "report-html-generation",
  "name": "report-html-generation",
  "raw_md": "...",       // SKILL.md 原文
  "files": [
    { "path": "templates/cover.html",
      "content": "<!doctype html>...",   // UTF-8 文件
      "size": 2841 },
    { "path": "assets/logo.png",
      "content_b64": "iVBORw0K...",     // 二进制文件
      "size": 9214 },
    { "path": "huge_dataset.csv",
      "truncated": true,                // > 1 MB
      "size": 5800001 }
  ]
}
```

客户端 `cloud_skills.rs` 用这个 endpoint 拷贝整个 skill 目录到
`~/.omicos/cloud-skills/skills/<id>/`，让 `skill_resource` 工具能读
到非 SKILL.md 文件。

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
2026-05 起 agent / skill 各有一套（PR #11、#12、#117 + 后续）：

```python
# agents
_AGENT_PROJECTED_KEYS = (
    "id", "name", "description", "icon",
    "tier", "version", "toolsets", "skills",
    "category", "category_order",
    "summary", "use_when", "example_prompts",
)

# skills
_SKILL_PROJECTED_KEYS = (
    "id", "name", "title", "description",
    "tier", "version",
    "category", "category_order",
    "summary", "use_when",
)
```

加了未识别的 frontmatter 字段，admin 会忽略——这是兼容性策略，让
将来加新字段不破坏老客户端。

```{admonition} raw_md 是逐字节同步的源
:class: tip

虽然 admin 投影 JSON 时会过滤未知字段，**`raw_md` 字段始终是 SKILL.md
/ agent.md 的完整原文**（PR omicos-core #124）。客户端 cache 写的
就是 `raw_md`——不认识的字段也保留下来。这意味着 admin 加了新字段
而客户端还没升级时，本地缓存依然完整，等客户端升级后自然就能解析
新字段。
```

## hash 算法（2026-05 起覆盖整个目录）

历史：`blake2b(SKILL.md bytes)`——只对 SKILL.md 敏感。

现在：sha256 over `(SKILL.md body, sorted (resource_path, content))`——
任何 reference.md / templates/cover.html / assets/* 改动都会触发
hash 变化，客户端增量同步会重拉。

副作用：现在改 reference.md 也会**对 admin manifest 版本号 + 1**，
客户端下次 sync 会下载一遍整个 skill。这是设计选择——优先正确性
（避免静默漂移），而不是带宽。

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
