# 加一个 toolset

回忆 [Agent / Team / Toolset](../concepts/01-agent-team-toolset.md)：
toolset 是工具的命名集合。agent 写 `toolsets: [- web]` 就能拿到
`web_search + web_fetch` 一整组。本章演示如何**新增一个 toolset 组**。

## 决定先：是新组还是扩老组

如果你只是给现有组加一个工具（比如 `web` 多一个 `web_summarize`），
直接到 `tool_providers/web.rs` 加 `ToolInfo` + 实现即可，不需要
toolset 改动。

如果你的工具集**语义独立**（比如新加一组"protein structure" 工具），
才走"新组"流程。下面以 `bio_struct` 为例。

## 步骤 1：实现 ToolProvider

在 `src/tool_providers/` 下加 `bio_struct.rs`：

```rust
use anyhow::{anyhow, Result};
use async_trait::async_trait;
use serde_json::{json, Value};
use crate::tool_providers::{ToolContext, ToolInfo, ToolProvider};

pub struct BioStructProvider;

#[async_trait]
impl ToolProvider for BioStructProvider {
    fn name(&self) -> &str { "bio_struct" }

    async fn list_tools(&self) -> Vec<ToolInfo> {
        vec![
            ToolInfo::new(
                "alphafold_fetch",
                "Pull AlphaFold structure for a UniProt ID. \
                 Returns CIF URL + pLDDT summary.",
                json!({
                    "type": "object",
                    "properties": {
                        "uniprot_id": {"type": "string"}
                    },
                    "required": ["uniprot_id"]
                }),
            ),
            ToolInfo::new(
                "seq_blast",
                "Run NCBI BLAST against nr/nt for a sequence. ...",
                json!({/* schema */}),
            ),
        ]
    }

    async fn call_tool(&self, tool: &str, args: Value, _ctx: &ToolContext) -> Result<Value> {
        match tool {
            "alphafold_fetch" => self.alphafold_fetch(args).await,
            "seq_blast" => self.seq_blast(args).await,
            _ => Err(anyhow!("bio_struct does not expose `{tool}`")),
        }
    }
}

impl BioStructProvider {
    async fn alphafold_fetch(&self, args: Value) -> Result<Value> {
        let uniprot = args["uniprot_id"].as_str()
            .ok_or_else(|| anyhow!("uniprot_id required"))?;
        // 调 https://alphafold.ebi.ac.uk/api/prediction/<uniprot>
        // 返回 {url, pLDDT}
        Ok(json!({"...": "..."}))
    }
    // ...
}
```

## 步骤 2：注册到 registry

`src/tool_providers/builtin.rs`（或新文件 `bio_struct.rs`）的
`build_default_registry`：

```rust
registry.register(Box::new(BioStructProvider));
```

## 步骤 3：加到 TOOLSET_GROUPS

`tool_providers/mod.rs`：

```rust
const TOOLSET_GROUPS: &[(&str, &[&str])] = &[
    // ...existing...
    ("bio_struct", &["alphafold_fetch", "seq_blast"]),
];
```

## 步骤 4：让 agent 使用

```yaml
# admin/agents/structure_explorer.md
toolsets:
  - file_manager
  - web
  - bio_struct       # ← 新组
skills:
  - alphafold-fetch  # 配套 skill
```

## 步骤 5：测试

```rust
// tests/tool_providers.rs
#[test]
async fn bio_struct_exposes_two_tools() {
    let agent = agent_with(&["bio_struct"]);
    let registry = build_default_registry(...);
    let schemas = resolve_agent_tool_schemas(&agent, &registry).await;
    let names: Vec<&str> = schemas.iter()
        .filter_map(|s| s["function"]["name"].as_str())
        .collect();
    assert!(names.contains(&"alphafold_fetch"));
    assert!(names.contains(&"seq_blast"));
}
```

## 设计取舍

- **toolset 边界**：每个组应该是 LLM 一次决策能用上的工具集合。
  超过 6 个工具的组通常说明该拆。
- **schema 严谨**：JSON Schema 写错 → LLM 提供错的参数 → 工具
  failure。把所有 required 字段、enum、format 都写明。
- **错误信息**：`Err(anyhow!("..."))` 的内容会原样发给 LLM。写得
  让 LLM **能纠正**——"required `uniprot_id`" 比 "missing field"
  好得多。

## 进一步

- [Tool execution pipeline](../omicos-core/04-tool-pipeline.md)
- [写一个 tool provider plugin](05-tool-provider-plugin.md)（更高级）
