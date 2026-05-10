# 鉴权

admin 在鉴权上的核心原则：**`/api/public/*` 全无鉴权，admin panel 用
basic auth + scrypt 哈希存放**。

## 三种 endpoint 类别

| 类别 | Path 前缀 | 鉴权 |
|---|---|---|
| Public | `/api/public/*` | 无 |
| Admin panel UI | `/admin/*` | HTTP Basic auth |
| Admin write API | `/api/admin/*` | HTTP Basic auth |

## Basic auth 配置

systemd drop-in 配置文件：

```ini
# /etc/systemd/system/omicos-admin.service.d/password.conf
[Service]
Environment="OMICOS_ADMIN_USERNAME=omicos"
Environment="OMICOS_ADMIN_PASSWORD_HASH=scrypt:32768:8:1$..."
```

password hash 是 werkzeug 的 `generate_password_hash` 产物：

```python
from werkzeug.security import generate_password_hash
print(generate_password_hash("@Sheep121"))  # → scrypt:32768:8:1$...
```

把输出整段（包括 `scrypt:...` 前缀）写到 `OMICOS_ADMIN_PASSWORD_HASH`。

`systemctl restart omicos-admin` 后生效。

## Cookie / session

admin panel 登录后下发 secure cookie。`OMICOS_ADMIN_SECURE_COOKIE=1`
强制 HTTPS-only——生产必须开。

## 客户端不需要 token

omicos-core 的客户端**只调** `/api/public/*`——所以**永远不需要**
admin 用户名密码。如果客户端代码里出现 admin 凭据，那是设计错误。

## 进一步

- [部署](04-deployment.md) — systemd / nginx
- [数据布局](01-data-layout.md)
