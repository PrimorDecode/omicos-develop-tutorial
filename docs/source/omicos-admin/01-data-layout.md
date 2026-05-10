# 数据目录与文件结构

omicos-admin 是 stateless Flask 应用——所有 catalog 数据都在
**文件系统**而不是数据库里。这一选择让 admin 可以靠
`scp` / `tar` / `rsync` 完成 backup / restore，不依赖任何 DBMS。

## 数据目录根

由 systemd 配置的 `OMICOS_ADMIN_DATA` 环境变量决定，默认
`/var/omicos-admin`：

```
/var/omicos-admin/
├── agents/
│   ├── omicverse_omni.md
│   ├── literature_scout.md
│   ├── clinical_translator.md
│   ├── paper_critic.md
│   └── .versions/<id>/<ts>.md   # 自动归档
├── skills/
│   ├── pubmed-search/
│   │   ├── SKILL.md
│   │   └── reference.md         # 可选
│   ├── biorxiv-monitor/
│   │   └── SKILL.md
│   └── ...
└── models.json                  # provider catalog
```

## 文件即 API

写入 `/var/omicos-admin/skills/<id>/SKILL.md` 等于发布。Flask
**每次请求**重扫这个目录，无需重启 service。所有公开 endpoint 都是
"读文件 → 解析 frontmatter → 拼 JSON 返回"的纯函数。

## Agent 自动版本化

每次 `/api/admin/agents/<id>` PUT 改动，旧版本被存档到
`.versions/<id>/<ts>.md`。便于回滚，也方便排查"昨天好好的，今天怎么
就坏了"。

skill **不**自动版本化——skill 改动建议先本地 git commit。

## models.json shape

```text
{
  "providers": [
    {
      "id":          "deepseek",
      "label":       "DeepSeek",
      "api_base":    "https://api.deepseek.com/v1",
      "env_var_name":"DEEPSEEK_API_KEY",
      "models": [
        {"id": "deepseek-chat", "label": "DeepSeek-V3", "context_window": 64000}
      ]
    },
    …
  ]
}
```

20+ provider 都在一份 JSON 里。客户端 sync 时整体下载（小，<10KB）。

## 备份 / 恢复

```bash
# 备份
ssh root@admin-host "tar czf /tmp/omicos-admin-backup.tgz \
    -C /var omicos-admin"
scp root@admin-host:/tmp/omicos-admin-backup.tgz ~/Desktop/

# 恢复（先 stop service）
ssh root@admin-host "systemctl stop omicos-admin && \
    tar xzf /tmp/omicos-admin-backup.tgz -C / && \
    systemctl start omicos-admin"
```

## 进一步

- [公开 API](02-public-api.md)
- [鉴权](03-auth.md)
- [部署](04-deployment.md)
