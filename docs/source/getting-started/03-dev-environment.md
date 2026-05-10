# 本地开发环境搭建

最少需要三套工具链：**Rust**（sidecar）+ **Node/pnpm**（前端）+
**Python venv**（内核）。本章在 macOS / Linux 下走通一次。Windows
需要额外步骤，见末尾的 caveat。

## 系统要求

| 工具 | 最低版本 | 推荐 |
|---|---|---|
| Rust toolchain | 1.78 | 通过 `rustup` 装，stable channel |
| Node.js | 20.x | 通过 `nvm` 或 `fnm` 管理 |
| pnpm | 9.x | `npm i -g pnpm@latest` |
| Python | 3.11 | venv 模式 |
| `gh` (GitHub CLI) | 任意 | clone + PR 流程都用得着 |

```{admonition} Tauri 系统依赖
:class: note

macOS 装 Xcode CLI tools 即可（`xcode-select --install`）。Linux
要装 `libwebkit2gtk-4.1-dev` / `libssl-dev` / `librsvg2-dev` 等，
完整列表见 [Tauri 官方 prereqs](https://tauri.app/start/prerequisites/)。
```

## Clone 仓库

```bash
mkdir -p ~/work/omicverse-project && cd ~/work/omicverse-project

gh repo clone PrimorDecode/omicos-core
gh repo clone PrimorDecode/omicos-ui     # 注意：仓库名小写
gh repo clone PrimorDecode/omicos-develop-tutorial
# omicos-admin 是内部仓库 — 找对应 maintainer 加访问权
```

## 装 Rust 工具链

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# 一些 IDE / 检查器需要这两个组件
rustup component add clippy rustfmt
```

验证：

```bash
cd omicos-core && cargo check 2>&1 | tail -3
# 期望: Finished `dev` profile [unoptimized + debuginfo]
```

## 装 Node + pnpm

```bash
# 推荐用 fnm
brew install fnm
fnm install 20 && fnm use 20

npm i -g pnpm@latest
```

验证：

```bash
cd omicos-ui && pnpm install
pnpm dev          # 启动 vite dev server，先不连 Tauri
```

## 装内核 venv

OmicOS 用的内核环境本身就是个独立 Python venv，安装的包是 `omicverse`
+ scientific stack。开发期最简单的做法是直接用 omicos-env 仓库的
锁文件：

```bash
cd omicos-env
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
deactivate
```

这一步比较慢（要装 numpy / pandas / scanpy / omicverse 等），第一次
20 分钟左右。装完之后 sidecar 自动从这里发现内核解释器（环境变量
`OMICOS_ENV_DIR` 默认指向 `~/.../omicos-env`）。

## 一次完整跑起来

```bash
# 1. 编 sidecar
cd ~/work/omicverse-project/omicos-core
cargo build --release
# 产物: target/release/omicos

# 2. 拷到 ui 的 sidecar 路径
cp target/release/omicos \
   ../omicos-ui/src-tauri/binaries/omicos-aarch64-apple-darwin
# Linux 用 omicos-x86_64-unknown-linux-gnu，Windows 用 omicos-x86_64-pc-windows-msvc.exe

# 3. 启动桌面端开发模式
cd ../omicos-ui
pnpm tauri dev
```

`pnpm tauri dev` 会同时跑 vite + Rust 容器 + sidecar 三件事。SPA 改动
HMR；Rust 容器 / sidecar 改动需要 Ctrl+C 重启。

```{admonition} 不想等编译？只调前端
:class: tip

把已经装好的 `/Applications/OmicOS.app` 跑起来，前端代码改动用
`pnpm dev` 在浏览器里调，sidecar URL 写
`http://127.0.0.1:<port>`（看 app 进程 lsof -i 找端口）——这样改 UI
完全不用 Rust 编译。
```

## 环境变量速查表

只列开发期常用的：

| 变量 | 含义 |
|---|---|
| `OMICOS_ENV_DIR` | 内核 venv 根目录 |
| `OMICOS_AGENTS_CACHE_DIR` | 覆盖 agent 缓存路径（默认 `~/.omicos/cloud-agents`） |
| `OMICOS_AGENTS_CLOUD_URL` | 覆盖 admin 拉取 URL |
| `OMICOS_AGENTS_OFFLINE` | `1` 关闭 sync，所有 agent 走本地模板 |
| `OMICOS_SKILL_ROOTS` | `:` 分隔的额外 skill 根（覆盖默认） |
| `OMICOS_TEMPLATES_DIR` | 覆盖 agent 模板根 |
| `RUST_LOG` | 推荐 `omicos_core=debug` 看完整 trace |

## Windows caveat

OmicOS 在 Windows 上**可以**编译，但官方目前只验证 macOS / Linux。
主要 caveats：

- 内核 venv 路径分隔符差异——Tauri sidecar 拉 Python 时已处理
- DMG bundling 不可用，桌面端只产 `.exe` + MSI
- gemini-cli OAuth 需要确保 Windows defender 不拦截重定向 URL

社区贡献欢迎，但请单独在 PR 里标 `windows-only`。

## 进一步

- [第一次构建](04-first-build.md) — release 流程 + 装机
- 出问题先看 [error-handling](../omicos-core/06-error-handling.md)
