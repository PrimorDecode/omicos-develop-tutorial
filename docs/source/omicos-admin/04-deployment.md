# 服务器部署

omicos-admin 跑在 Linux 上 + Gunicorn + systemd + nginx 反向代理。
本章总结生产配置。

## systemd unit

```ini
# /etc/systemd/system/omicos-admin.service
[Unit]
Description=OmicOS Admin (agent-prompt management)
After=network.target

[Service]
Type=simple
User=omicos-admin
Group=omicos-admin
WorkingDirectory=/opt/omicos-admin
Environment="OMICOS_ADMIN_DATA=/var/omicos-admin"
Environment="OMICOS_ADMIN_HOST=127.0.0.1"
Environment="OMICOS_ADMIN_PORT=5070"
Environment="OMICOS_ADMIN_SECURE_COOKIE=1"
ExecStart=/opt/omicos-admin/.venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:5070 \
    --access-logfile - \
    --error-logfile - \
    --timeout 30 \
    app:app
Restart=on-failure
RestartSec=3
StandardOutput=journal
StandardError=journal

# Hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/omicos-admin
ProtectKernelTunables=yes
ProtectKernelModules=yes

[Install]
WantedBy=multi-user.target
```

凭据用 systemd drop-in 单独管：

```
/etc/systemd/system/omicos-admin.service.d/
├── admin-api.conf       # 端口 / 主机
└── password.conf        # OMICOS_ADMIN_USERNAME / PASSWORD_HASH
```

## nginx 反代

```nginx
server {
    listen 443 ssl http2;
    server_name admin.omicverse.com;

    ssl_certificate     /etc/letsencrypt/live/.../fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/.../privkey.pem;

    # 公开 API + admin panel 都过这里
    location / {
        proxy_pass http://127.0.0.1:5070;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 升级流程

见 [运维 / admin 升级](../operations/02-admin-upgrade.md)。

## 监控

- `journalctl -u omicos-admin -f` 看实时日志
- `/api/health` 端点（如果实现）做 uptime check
- 文件系统：`/var/omicos-admin` 占用 < 10MB 长期，超了说明
  `.versions/` 累积太多，可定期清

## 进一步

- [数据布局](01-data-layout.md)
- [鉴权](03-auth.md)
- [运维 / 数据迁移](../operations/03-data-migration.md)
