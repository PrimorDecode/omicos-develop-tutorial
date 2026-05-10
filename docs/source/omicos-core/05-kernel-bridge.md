# Kernel 通信

OmicOS 的"跑 Python 代码"工具背后是一个真正的 IPython 内核进程，
sidecar 通过 ZMQ 与之通信。这一层是计算栈的核心。

## 为什么不直接 `subprocess.run("python", ...)`

需要：

- **持久会话**：`adata = sc.read_h5ad(...)` 之后下一次 `adata.shape`
  得拿到同一个对象——subprocess 做不到
- **图表渲染**：matplotlib 内联输出、HTML 表格、IPython display 都
  靠 `display_data` 协议
- **流式输出**：长任务边跑边出 stdout，不能等完整

IPython kernel + ZMQ 都搞定。

## 启动

sidecar 在启动时定位 Python：

1. `OMICOS_ENV_DIR` 指向的 venv（生产）
2. fallback：往上找 sibling 路径（开发 / 应急）

然后：

```rust
Command::new(python_bin)
    .args(["-m", "ipykernel_launcher",
           "-f", &connection_file_path])
    .spawn()
```

ZMQ connection file 是个 JSON，写明 5 个 socket 端口（shell / iopub /
stdin / control / heartbeat）。sidecar 用 `zmq` Rust crate 连。

## 主要消息

| 消息 | 方向 | 用途 |
|---|---|---|
| `execute_request` | sidecar → kernel | 执行代码 |
| `execute_reply` | kernel → sidecar | 执行结果（status + counter） |
| `stream` | kernel → sidecar (iopub) | stdout / stderr |
| `display_data` | kernel → sidecar (iopub) | 图表 / HTML 输出 |
| `error` | kernel → sidecar (iopub) | 异常 traceback |
| `kernel_info_request` | sidecar → kernel | 健康探活 |

## AnnData state 抓取

`adata_state` 工具读内核里的 `adata` 变量并返回 schema。实现方式是
sidecar 注入一段 Python helper（`__omicos_inspect`）到内核的全局
namespace，然后 `execute_request` 调它，把 stdout 解析成结构化结果。

helper 是幂等可重入的——反复 inject 不出错。

## 错误恢复

- 内核 hang：`control` channel 发 `interrupt_request`
- 内核挂掉：sidecar 检测 zmq heartbeat 丢失 → 重启子进程；当前
  conversation 标"内核已重启，变量丢失"
- 内核 OOM：操作系统 OOM killer 杀掉进程 → 同上路径

## 进一步

- 工具入口看 [Tool pipeline](04-tool-pipeline.md)
- 错误恢复看 [Error handling](06-error-handling.md)
