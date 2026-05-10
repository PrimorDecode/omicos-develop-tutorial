# OmicOS 开发者文档

OmicOS 生态的中文开发者教程，使用 [Sphinx](https://www.sphinx-doc.org/) +
[furo](https://pradyunsg.me/furo/) 主题构建。

## 在线阅读

托管于 ReadTheDocs（待发布）。

## 本地构建

```bash
# 创建虚拟环境（可选）
python -m venv .venv && source .venv/bin/activate

# 安装依赖
make install

# 构建 HTML
make html

# 在 docs/build/html/index.html 打开查看
```

## 实时预览

```bash
pip install sphinx-autobuild
make livehtml
# 浏览器打开 http://127.0.0.1:8000
```

## 文档结构

```
docs/source/
├── index.md                    # 入口
├── getting-started/            # 入门
├── concepts/                   # 核心概念
├── omicos-core/                # Rust sidecar 深度
├── omicos-ui/                  # Tauri 前端深度
├── omicos-admin/               # Flask admin 深度
├── extension-guides/           # 扩展开发
├── operations/                 # 运维 / 部署
└── contributing/               # 贡献指南
```

## 贡献

文档采用 Markdown（通过 [MyST 解析器](https://myst-parser.readthedocs.io/)），
直接 PR 即可。本仓库与 omicos 各代码仓库分离独立维护，**只有文档**。

代码相关问题请到对应仓库提：

| 模块 | 仓库 |
|---|---|
| Rust sidecar | [PrimorDecode/omicos-core](https://github.com/PrimorDecode/omicos-core) |
| Tauri 前端 | [PrimorDecode/omicos-ui](https://github.com/PrimorDecode/omicos-ui) |
| Flask admin | （内部仓库） |

## License

[MIT](LICENSE)
