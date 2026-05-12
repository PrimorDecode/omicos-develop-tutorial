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

sidecar 在启动时定位 Python。**所有定位入口都集中在
`native::resolve_python_interpreter()`** —— kernel 进程、`kernel_install`
工具、shell 子进程兜底全部走它（PR omicos-core #135 把 `python_command()`
也改成调它，避免 fallback 用了系统 Python 装到错的地方）。

定位顺序：

1. `OMICOS_KERNEL_PYTHON` 环境变量（dev override）
2. 工作区 `.omicos/.kernel_choice` 持久化的选择（用户在 SPA 改过）
3. `OMICOS_ENV_DIR/.venv/bin/python3`
4. autodiscover：从 `current_exe()` 向上找 `omicos-env` sibling（bundle
   的生产路径）
5. `PYTHON` 环境变量
6. `CONDA_PREFIX/bin/python3`
7. `VIRTUAL_ENV/bin/python3`
8. 系统 `python3`（最后兜底）

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
- **stdin EPIPE**（PR omicos-core #137）：往 worker 写 stdin 时拿到
  `BrokenPipe` 等同于 stdout EOF——说明 worker 死了，触发同样的 respawn
  路径。之前只对 stdout 端的 `UnexpectedEof` 反应，导致先写后读的工具
  会无限循环报 "Broken pipe"。
- **readiness 缓存非对称**：成功 5 s、失败 1 s，且失败时会自动再
  探一次（500 ms 后）——典型 case：刚装完一个 pip 包，kernel 自我
  重启的瞬间外面调 `/api/kernel/vars`，第一次失败、500 ms 后第二次
  成功，UI 不会闪一下 "kernel unreachable"。

## 进一步

- 工具入口看 [Tool pipeline](04-tool-pipeline.md)
- 错误恢复看 [Error handling](06-error-handling.md)
