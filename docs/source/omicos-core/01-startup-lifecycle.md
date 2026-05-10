# 启动与生命周期

sidecar 从 Tauri 拉起到接受第一个 chat 请求中间发生的事，按时间顺序：

## 启动序列

1. **Tauri 容器**（`src-tauri/src/lib.rs`）调用
   `tauri-plugin-shell` 拉子进程，binary 路径
   `binaries/omicos-<target>`。
2. sidecar 读环境变量 + CLI args 决定 workspace、admin URL、cache 目录。
3. sidecar 选一个本地随机端口（避开冲突），写
   `<workspace>/.omicos/serve.pid`：`<pid>\n<port>\n`。
4. sidecar 后台异步启动以下：
   - 异步 sync agent / skill / model catalog（best-effort，失败不阻塞）
   - 启动 IPython 内核子进程（`python -m ipykernel_launcher` via ZMQ）
   - 启动 axum HTTP server，绑 `127.0.0.1:<port>`
5. Tauri 容器轮询 `serve.pid` → 拿到端口 → SPA 用这个端口连 sidecar。

## 进程父子关系

```
omicos-desktop (Tauri Rust shell)
└── omicos       (omicos-core sidecar)
    └── python   (IPython kernel)
        └── … 用户代码起的子进程
```

## 死亡处理

omicos-desktop 监听 sidecar stdout/stderr。当 sidecar 异常退出：

- 退出码非 0 + `BackendState.child` 还在 → **自动重启**（800ms 退避）
- 致命错误（workspace conflict、read-only fs、port stolen）→ 不重启，
  发 `kernel-fatal-error` event 给 SPA → SPA 弹原生 confirm，让用户
  点"重试"才再启动

源码：[`omicos-ui/src-tauri/src/lib.rs`](https://github.com/PrimorDecode/omicos-ui/blob/main/src-tauri/src/lib.rs)。

## 关闭

只在 SPA 主窗（`window.label() == "main"`）关闭时杀 sidecar。
auto-key 之类的子窗关闭**不**触发——避免子窗关闭意外杀死后端
（PR #105 修复）。

## 进一步

- [HTTP API](02-http-api.md) — sidecar 暴露的所有 endpoint
- [错误处理](06-error-handling.md) — 致命错误分类 + 自恢复
