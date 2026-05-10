# OmicOS 开发者文档

欢迎。这是 OmicOS 生态的中文开发者教程。我们假设你已经会用桌面端，希望
*往里面写代码*——加 skill、加 agent、改 sidecar、调 admin、定制 UI。

如果你只是想用 OmicOS 做生信分析，参考 [omicverse-tutorials](https://github.com/PrimorDecode/omicverse-tutorials)，那是用户向手册。

```{admonition} 本文档基于的版本
:class: note

omicos-core ≥ 0.2.0、omicOS-ui ≥ 0.1.0。某些章节的代码引用可能略快于
最新 release，但核心架构相对稳定，所有结论都注明了源码路径，可对照阅读。
```

---

## 你最关心的入口

::::{grid} 1 2 2 3
:gutter: 3

:::{grid-item-card} 🚀 第一次贡献？
:link: getting-started/01-vision-and-architecture
:link-type: doc

从 [架构总览](getting-started/01-vision-and-architecture.md) 起步，然后
[搭一个能跑的本地环境](getting-started/03-dev-environment.md)。
:::

:::{grid-item-card} 🧠 想理解核心概念
:link: concepts/01-agent-team-toolset
:link-type: doc

跳到 [Agent / Team / Toolset 模型](concepts/01-agent-team-toolset.md) 和
[Skill 系统](concepts/02-skills-system.md)。
:::

:::{grid-item-card} 🔧 直接来加功能
:link: extension-guides/01-add-a-skill
:link-type: doc

看 [写一个 skill](extension-guides/01-add-a-skill.md) 或
[写一个 agent](extension-guides/02-add-an-agent.md)。
:::

::::

---

## 文档地图

```{toctree}
:caption: 入门
:maxdepth: 2

getting-started/01-vision-and-architecture
getting-started/02-repos-and-roles
getting-started/03-dev-environment
getting-started/04-first-build
```

```{toctree}
:caption: 核心概念
:maxdepth: 2

concepts/01-agent-team-toolset
concepts/02-skills-system
concepts/03-providers-and-protocols
concepts/04-workspace-and-conversation
concepts/05-cloud-sync
```

```{toctree}
:caption: omicos-core (Rust sidecar)
:maxdepth: 2

omicos-core/01-startup-lifecycle
omicos-core/02-http-api
omicos-core/03-streaming-sse
omicos-core/04-tool-pipeline
omicos-core/05-kernel-bridge
omicos-core/06-error-handling
```

```{toctree}
:caption: omicos-ui (Tauri 前端)
:maxdepth: 2

omicos-ui/01-architecture
omicos-ui/02-sidecar-lifecycle
omicos-ui/03-stores
omicos-ui/04-build-and-bundle
```

```{toctree}
:caption: omicos-admin (Flask)
:maxdepth: 2

omicos-admin/01-data-layout
omicos-admin/02-public-api
omicos-admin/03-auth
omicos-admin/04-deployment
```

```{toctree}
:caption: 扩展开发
:maxdepth: 2

extension-guides/01-add-a-skill
extension-guides/02-add-an-agent
extension-guides/03-add-a-provider
extension-guides/04-add-a-toolset
extension-guides/05-tool-provider-plugin
```

```{toctree}
:caption: 运维 / 部署
:maxdepth: 2

operations/01-desktop-bundle
operations/02-admin-upgrade
operations/03-data-migration
```

```{toctree}
:caption: 贡献指南
:maxdepth: 2

contributing/01-git-workflow
contributing/02-style-and-tests
contributing/03-pr-template
```

---

## 文档维护

本文档的源码位于
[PrimorDecode/omicos-develop-tutorial](https://github.com/PrimorDecode/omicos-develop-tutorial)。
任何错误、过时章节、希望补充的内容，欢迎直接提 PR——文档和代码同等重要。

文档采用 Markdown（通过 [MyST 解析器](https://myst-parser.readthedocs.io/)），
不需要学习 reStructuredText。

License: [MIT](https://github.com/PrimorDecode/omicos-develop-tutorial/blob/main/LICENSE)。
