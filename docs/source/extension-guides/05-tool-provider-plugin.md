# 写一个 tool provider plugin

`src/plugins/` 下的 provider 和 `src/tool_providers/builtin.rs`
里的 provider 是同一接口（都实现 `ToolProvider` trait），但**目录
分布**反映了不同的关注点：

| 位置 | 用途 |
|---|---|
| `tool_providers/builtin.rs` | sidecar 自带、跨 OmicOS 普适的工具 |
| `plugins/<name>.rs` | 业务/集成性更强的工具，例如 memory、task、第三方 SaaS |

如果你的工具：

- 依赖外部 API key 配置
- 涉及独立的可选功能（用户可能不开）
- 体量较大（多个文件）

——放到 `plugins/`。否则放到 `tool_providers/`。

## 例子：为 OmicOS 加 Slack 通知 plugin

agent 跑完一个长任务后给用户发 Slack 消息。完整骨架：

```
src/plugins/slack.rs
```

```rust
use anyhow::{anyhow, Context, Result};
use async_trait::async_trait;
use serde_json::{json, Value};
use crate::tool_providers::{ToolContext, ToolInfo, ToolProvider};

pub struct SlackProvider {
    webhook_url: Option<String>,
}

impl SlackProvider {
    pub fn from_env() -> Self {
        Self {
            webhook_url: std::env::var("OMICOS_SLACK_WEBHOOK").ok()
                .filter(|s| !s.trim().is_empty()),
        }
    }
}

#[async_trait]
impl ToolProvider for SlackProvider {
    fn name(&self) -> &str { "slack" }

    async fn list_tools(&self) -> Vec<ToolInfo> {
        if self.webhook_url.is_none() {
            // 未配置时不暴露工具——LLM 看不到，避免徒劳调用
            return vec![];
        }
        vec![ToolInfo::new(
            "slack__notify",
            "Send a Slack message via the user's configured webhook. \
             Use after long-running analyses to ping the user.",
            json!({
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "blocks": {"type": "array"}
                },
                "required": ["text"]
            }),
        )]
    }

    async fn call_tool(&self, tool: &str, args: Value, _ctx: &ToolContext) -> Result<Value> {
        if tool != "slack__notify" {
            return Err(anyhow!("slack provider does not expose `{tool}`"));
        }
        let url = self.webhook_url.as_deref()
            .ok_or_else(|| anyhow!("OMICOS_SLACK_WEBHOOK not set"))?;
        let text = args["text"].as_str()
            .ok_or_else(|| anyhow!("text required"))?;
        let body = json!({"text": text});
        if let Some(blocks) = args.get("blocks") {
            // optional rich blocks
            let _ = blocks;
        }
        let resp = reqwest::Client::new()
            .post(url)
            .json(&body)
            .send()
            .await
            .with_context(|| format!("POST slack webhook"))?;
        if !resp.status().is_success() {
            return Err(anyhow!("slack returned {}", resp.status()));
        }
        Ok(json!({"sent": true}))
    }
}
```

## 注册

`src/plugins/mod.rs`：

```rust
pub mod slack;
```

`src/lib.rs` 或 `tool_providers/builtin.rs::build_default_registry`：

```rust
registry.register(Box::new(crate::plugins::slack::SlackProvider::from_env()));
```

## 加到 toolset

`tool_providers/mod.rs`：

```rust
const TOOLSET_GROUPS: &[(&str, &[&str])] = &[
    // ...
    ("notify", &["slack__notify"]),
];
```

## 让 agent 用

```yaml
toolsets:
  - integrated_notebook
  - notify    # 新组
```

## 设计原则

1. **未配置 → 工具隐形**。`list_tools()` 返回空——LLM 不会看到、不会
   猜调，不会污染 system prompt token。
2. **凭据来自环境变量或 keychain**，**不**从对话上下文里取。
3. **失败显式**——`Err` 而不是返回 `{"sent": false}`。LLM 拿到
   `status: "error"` 才知道要重试 / 提示用户。
4. **写单测**——至少 fixture-driven 的 schema 校验测试。

## 进一步

- [加一个 toolset](04-add-a-toolset.md) — 简单版本
- [Tool execution pipeline](../omicos-core/04-tool-pipeline.md)
