# omicos-admin 升级

admin 是 stateless Flask 应用——升级流程简洁。

## 标准流程（< 1 分钟停机）

```bash
ssh root@admin-host

# 1. 拉新代码
cd /opt/omicos-admin
sudo -u omicos-admin git pull --ff-only origin main

# 2. 装新依赖（如有）
sudo -u omicos-admin /opt/omicos-admin/.venv/bin/pip install -r requirements.txt

# 3. 重启
systemctl restart omicos-admin

# 4. 验证
systemctl is-active omicos-admin
curl -s http://127.0.0.1:5070/api/public/agents/manifest | python3 -c \
    'import json,sys;d=json.load(sys.stdin);print("agents:",len(d["agents"]))'
```

正常返回应该 < 5 秒。

## 滚回

代码回滚：

```bash
sudo -u omicos-admin git log --oneline -5    # 找上一个 sha
sudo -u omicos-admin git reset --hard <sha>
systemctl restart omicos-admin
```

`/var/omicos-admin/` 的数据**不动**——回滚只回滚代码，不回滚 catalog。

## 数据库迁移

omicos-admin 当前不用数据库，**不存在 migration 概念**。
catalog 改动直接是文件改动，不需要 schema migration。

## 升级检查清单

- [ ] `systemd` drop-in 配置（password.conf / admin-api.conf）保持
      不变——这些是机器特定的，不要 commit
- [ ] python 包没有破坏性升级（看 `git diff requirements.txt`）
- [ ] `_PROJECTED_KEYS` 如果加了字段，*所有客户端 ≥ 这个版本*才能识别——
      否则旧客户端会丢字段
- [ ] `/api/public/skills/manifest` 拉得回来
- [ ] `/api/public/agents/manifest` 拉得回来
- [ ] admin panel 能登录

## 进一步

- [部署 / systemd 配置](../omicos-admin/04-deployment.md)
- [数据迁移](03-data-migration.md)
