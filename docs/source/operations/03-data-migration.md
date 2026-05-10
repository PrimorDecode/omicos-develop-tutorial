# 数据迁移

OmicOS 的"数据"分两类：

- **服务器侧**：`/var/omicos-admin/` 下的 catalog（agents / skills /
  models）
- **客户端侧**：`~/Library/Application Support/com.omicverse.omicos/`
  + `~/.omicos/` 下的本地状态

两者的迁移考虑很不一样。

## 服务器迁移（admin → 新机器）

stateless 设计让迁移就是文件复制：

```bash
# 旧机器
ssh old-admin "tar czf /tmp/admin.tgz -C /var omicos-admin && \
                tar czf /tmp/code.tgz -C /opt omicos-admin"
scp old-admin:/tmp/{admin,code}.tgz ~/

# 新机器
scp ~/{admin,code}.tgz new-admin:/tmp/
ssh new-admin "tar xzf /tmp/admin.tgz -C /var && \
               tar xzf /tmp/code.tgz -C /opt && \
               systemctl daemon-reload && systemctl start omicos-admin"
```

DNS 切到新机器即可。客户端无感（admin URL 不变）。

## 客户端 schema 迁移

OmicOS 选了**永远向前兼容**的策略：

| 改动 | 客户端处理 |
|---|---|
| admin 新增 catalog 字段（如 `skills:` 加进 agent） | 老客户端 `serde(default)` 默认空，不崩 |
| admin 删除字段 | 客户端字段为 `Option`，缺字段视作 `None` |
| 客户端新增字段需求 | 服务器升级前，客户端要 `serde(default)` 兜底，避免假阳性破坏 |

这套约定意味着 **客户端先升级 / 服务器先升级 都不破坏既有用户**——
"两个版本互相能跑"是显式设计目标。

## 用户工作区迁移（备份 / 恢复）

用户切机器或重装系统：

```bash
# 备份
tar czf ~/Desktop/omicos-state.tgz \
    -C ~ Library/Application\ Support/com.omicverse.omicos \
    -C ~ .omicos

# 新机器恢复
tar xzf ~/Desktop/omicos-state.tgz -C ~
```

```{admonition} API key 例外
:class: warning

API key 落在 OS keychain（macOS Keychain / Windows Credential Manager），
**不在** 上述 tar 里。新机器需要重新填一次。这是 by design——keychain
不该被 tar。
```

## conversation 迁移到不同 workspace

直接 `cp <old-ws>/.omicos/conversations/*.json <new-ws>/.omicos/conversations/`。
session id 是文件名，UUID 形态，跨 workspace 唯一不冲突。

## skill 缓存损坏修复

```bash
rm -rf ~/.omicos/cloud-skills
# 下次 sidecar 启动会重新 sync
```

## 进一步

- [omicos-admin / 数据布局](../omicos-admin/01-data-layout.md)
- [Cloud sync](../concepts/05-cloud-sync.md)
