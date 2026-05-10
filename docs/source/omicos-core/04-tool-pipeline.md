# Tool execution pipeline

LLM 调"工具"在 OmicOS 里是个非平凡的过程。它经过 **schema 派发 →
provider 路由 → 执行边界检查 → 结果序列化 → 错误规范化** 5 个环节，
每一步都有具体的 Rust 模块负责。本章顺着一次 tool call 的生命周期
讲完。

## 入口：`ToolExecutor::run`

[`ToolExecutor`](https://github.com/PrimorDecode/omicos-core/blob/main/src/tools.rs)
是面向 LLM 的"工具入口"。当 provider 返回一个 tool call

```json
{ "id": "call_abc", "name": "run_python_code",
  "arguments": "{\"code\":\"adata.obs.head()\"}" }
```

sidecar 通过

```rust
executor.run(ToolRequest {
    id: "call_abc".into(),
    name: "run_python_code".into(),
    arguments: serde_json::from_str(...)?,
    session_id: Some(sess.into()),
}).await
```

把它派发到具体处理函数。`ToolExecutor::run` 是个大 match，按 `name`
路由到对应的 `async fn`：

```rust
let result = match request.name.as_str() {
    "run_python_code" | "python" => self.run_python_code(...).await,
    "shell"                       => self.run_shell(...).await,
    "file_manager__list"          => self.list_files(...).await,
    "file_manager__read"          => self.read_file(...).await,
    "notebook__inspect"           => self.notebook_inspect(...).await,
    // ... 几十个 arm
    "skill_lookup"                => self.skill_lookup(...).await,
    "list_agents"                 => self.list_agents().await,
    "call_agent"                  => Err(anyhow!("...should have been intercepted...")),
    other                         => Err(anyhow!("unknown tool: {other}")),
};
```

```{admonition} call_agent 的特殊路径
:class: note

`call_agent` 不在这里跑，它会被 `runtime::dispatch_call_agent` 在
执行器之前截下来——因为它要"以另一个 agent 为 active 重新跑一个子
turn"，整个生命周期完全不同。如果调用真的落到 ToolExecutor 这层，
意味着拦截失效，是 bug。
```

## 边界：`allow_shell` / `allow_file_write`

`ToolExecutor::new(workspace, allow_shell, allow_file_write)` 的两个
布尔参数是 **执行边界**。只要它们是 `false`，对应的工具就拒绝执行：

| 工具 | 受 `allow_shell` 限制 | 受 `allow_file_write` 限制 |
|---|---|---|
| `shell` | ✓ | — |
| `file_manager__write` | — | ✓ |
| `file_manager__edit` | — | ✓ |
| `file_manager__notebook_edit` | — | ✓ |

这两个开关 **不是 skill 白名单**——白名单决定 LLM 看不看得到，边界
开关决定 *看得到也跑不起来*。SPA 在每次 chat 请求时根据用户在 UI
点的"允许 shell / 允许写文件"按钮把这两个布尔传到 sidecar。

## Tool provider：把工具变成 LLM 看得见的 schema

LLM 调的是"工具"，但 LLM **首先得知道有哪些工具**。这步在
[`tool_providers/`](https://github.com/PrimorDecode/omicos-core/tree/main/src/tool_providers)
完成。

每个 provider 实现 `ToolProvider` trait：

```rust
#[async_trait]
pub trait ToolProvider: Send + Sync {
    fn name(&self) -> &str;
    async fn list_tools(&self) -> Vec<ToolInfo>;
    async fn call_tool(&self, tool: &str, args: Value, ctx: &ToolContext) -> Result<Value>;
}
```

- `list_tools()` 返回这个 provider 暴露给 LLM 的工具元数据
  （name + description + JSON schema）。sidecar 在构建 chat 请求时
  把所有 provider 的工具拼成 OpenAI / Anthropic 兼容的 `tools: [...]`
  数组。
- `call_tool()` 是 *fallback 执行入口*——`ToolExecutor::run` 处理不了
  的工具会落到这里。今天主要给 `team` 与 `skill` 这两个 native
  provider 用。

具体 provider：

| Provider | 暴露工具 | 实现位置 |
|---|---|---|
| `python_interpreter` | `run_python_code` | builtin.rs |
| `notebook` | `notebook__inspect` 等 | builtin.rs |
| `file_manager` | `file_manager__*` | builtin.rs |
| `shell` | `shell` | builtin.rs |
| `web` | `web_search`, `web_fetch` | web.rs |
| `team` | `list_agents`, `call_agent` | builtin.rs |
| `skill` | `skill` | builtin.rs（fallback 模式） |
| `omicverse_lookup` | `registry_lookup` | builtin.rs |
| `pdf` | `pdf__*` | builtin.rs |
| `image_gen` | `image_gen__generate` | image_gen.rs |
| `memory` | `memory__*` | plugins/memory.rs |

## 注册表：哪个 toolset 能拿到哪些 provider

agent frontmatter 写的是 *toolsets*（粗粒度），LLM 看到的是
*tools*（细粒度）。中间这层翻译在
[`tool_providers/mod.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/tool_providers/mod.rs)
的 `TOOLSET_GROUPS` + `resolve_agent_tool_schemas`：

```rust
const TOOLSET_GROUPS: &[(&str, &[&str])] = &[
    ("integrated_notebook", &["python", "notebook", "omicverse_lookup"]),
    ("web", &["web_search", "web_fetch"]),
    // ...
];
```

`resolve_agent_tool_schemas(agent, registry)` 做的事：

1. 读 `agent.toolsets`：`["integrated_notebook", "web", "memory"]`
2. 用 `TOOLSET_GROUPS` 展开：
   `["python", "notebook", "omicverse_lookup", "web_search", "web_fetch",
   "memory__*"]`
3. 在 `registry` 里查每个工具属于哪个 provider，调它的
   `list_tools()` 拿 schema
4. 返回 `Vec<serde_json::Value>` —— 直接是 OpenAI 兼容的 `tools[]`

## 执行：从 args 到 result

回到 `ToolExecutor::run`。任何具体的 `async fn`（比如
`run_python_code`）都遵循同一个轮廓：

```rust
async fn run_python_code(&self, args: &Value, sid: Option<&str>) -> Result<Value> {
    // 1. 解析参数（不信任 LLM）
    let code = args["code"].as_str()
        .or_else(|| args["content"].as_str())
        .ok_or_else(|| anyhow!("run_python_code requires code"))?;

    // 2. 边界 / 权限检查
    // (run_python_code 没有专门的开关，但其它工具会查 allow_shell 等)

    // 3. 执行 — 通常是 await 一个外部资源
    let kernel = self.kernel.as_ref()
        .ok_or_else(|| anyhow!("no kernel attached"))?;
    let exec = kernel.execute(code, sid).await?;

    // 4. 序列化结果
    Ok(json!({
        "stdout": exec.stdout,
        "stderr": exec.stderr,
        "display_data": exec.display_data,
        "error": exec.error,
    }))
}
```

返回的 `Value` 经 `stringify_tool_result` 或
`stringify_execution_result` 转成字符串，包裹进
`ToolCallInfo`，写进 trajectory，并作为下一轮 prompt 的
`role: "tool"` 消息塞回去。

## 错误的规范化

工具内部 `Err(...)` 不会让 turn 崩——`ToolExecutor::run` 末尾做了
统一兜底：

```rust
let (status, text) = match result {
    Ok(value) => ("done", stringify_tool_result(&value)),
    Err(err) => ("error", err.to_string()),
};
Ok(ToolCallInfo {
    status: status.to_string(),
    result: text,
    // ...
})
```

LLM 收到的永远是 `{"status": "...", "result": "..."}` 形态的字符串，
不会因为你 `bail!()` 把 turn 杀了。这意味着工具内部尽管放心抛错——
LLM 会看到错误信息，自己决定下一步。

## 跟踪：trajectory + tracing

每次工具执行都会留下两条记录：

1. **trajectory**：`<workspace>/.omicos/trajectories/<session>/...`
   下的 JSONL，记完整的 `ToolCallInfo`——给"回放对话"功能用。
2. **tracing 日志**：`omicos-core` 用 `tracing` 框架，工具开始/结束
   各打一条 debug，结束时附带 `elapsed_ms` + `result_chars` + `status`：

```rust
tracing::debug!(
    tool_id = %request.id,
    tool_name = %request.name,
    status,
    elapsed_ms = started.elapsed().as_millis(),
    result_chars = text.chars().count(),
    "tool execution finished"
);
```

启动时设 `RUST_LOG=omicos_core=debug` 可以看到完整的工具流水。

## 想加一个新工具？

- 工具属于现有 toolset 组：直接在 `tool_providers/builtin.rs` 加
  `ToolInfo` + match arm，再到 `TOOLSET_GROUPS` 把名字加到对应组。
- 完整新组：[加一个 toolset](../extension-guides/04-add-a-toolset.md)。
- 一个全新的 provider（外部 API、新模型）：
  [写一个 tool provider plugin](../extension-guides/05-tool-provider-plugin.md)。
