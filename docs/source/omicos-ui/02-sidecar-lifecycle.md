# Sidecar 生命周期管理

Tauri Rust shell 负责拉起 / 监控 / 重启 sidecar。这一层是用户体感
"OmicOS 起得来"的关键。

## Sidecar spawn

[`src-tauri/src/lib.rs`](https://github.com/PrimorDecode/omicos-ui/blob/main/src-tauri/src/lib.rs)
里 `setup` hook 中：

```rust
let sidecar = app.shell().sidecar("omicos")?
    .args(["--port", "0"])
    .spawn()?;
```

binary 文件来自 `src-tauri/binaries/omicos-<target>`——构建前必须
拷过来（[第一次构建](../getting-started/04-first-build.md)）。

## 端口发现

sidecar 不接受 `--port` 直接绑——它选随机端口避冲突，把
`pid\nport\n` 写到 `<workspace>/.omicos/serve.pid`。

Tauri shell 启动后开始**轮询** `serve.pid` 文件：

- 读到 → 解析端口 → push 到 SPA 的 store（通过 Tauri event）
- SPA 拿到端口才能连 sidecar

## stderr ring buffer

sidecar 的 stderr 流被 Tauri shell 读到，保留**最近 30 行**用于致命
错误时附在 `kernel-fatal-error` event 里。这样 SPA 弹的 confirm 框
能给用户看具体错误。

## 自动重启

`CommandEvent::Terminated` 触发后：

```rust
if state.child.is_some() {
    sleep(Duration::from_millis(800)).await;
    spawn_sidecar(...).await?;
}
```

`state.child` 在用户主动关窗时会被清空，所以正常关闭不会无限循环
重启。

## 致命错误分类

读最近 30 行 stderr，按关键字分类成：

| kind | 触发条件 |
|---|---|
| `workspace_conflict` | 同 workspace 已经有另一个 sidecar 跑 |
| `read_only_workspace` | 工作区无写权限 |
| `port_conflict` | 端口被占（罕见——sidecar 自己选随机口） |
| `unknown` | 上面都不匹配 |

emit `kernel-fatal-error: {kind, title, raw_stderr, exit_code}` 给 SPA。

## 主窗 close 才杀 sidecar

```rust
app.on_window_event(|window, event| {
    if let WindowEvent::CloseRequested { .. } = event {
        if window.label() == "main" {
            kill_sidecar();
        }
        // 子窗（auto-key 等）忽略
    }
});
```

PR #104 + #105 修的"sidecar 莫名其妙挂"问题就是这里——以前没区分
窗口 label。

## 进一步

- [Pinia stores](03-stores.md) — 端口怎么传到 SPA
- [omicos-core 启动 / 生命周期](../omicos-core/01-startup-lifecycle.md)
