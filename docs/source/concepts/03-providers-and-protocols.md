# Provider / Protocol 抽象

OmicOS 不绑定任何一家 LLM 厂商。"调一次 LLM"在 sidecar 里抽象成
**Provider + Protocol** 两层。

## Provider — 一个具体的端点配置

`ProviderConfig`（[`providers.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/providers.rs)）
是一次 chat 调用的全部所需：

```rust
pub struct ProviderConfig {
    pub provider: String,           // "openai" / "deepseek" / "moonshot" / ...
    pub model: String,              // "gpt-5" / "kimi-k2.6" / ...
    pub base_url: String,           // 完整 URL（catalog-driven）
    pub api_key: Option<String>,
    pub account_id: Option<String>, // Codex OAuth
    pub project_id: Option<String>, // Gemini Code Assist
    pub protocol: ProviderProtocol,
    pub temperature: Option<f32>,   // 已废弃 — 见 PR #112
}
```

provider 名 + base URL 现在都从 admin 的 `models.json` catalog 读，
sidecar 不再硬编码任何 URL（PR #111）。

## Protocol — 三种说话方式

OmicOS 实现了 3 种协议：

| Protocol | 端点形态 | 兼容厂商 |
|---|---|---|
| `ChatCompletions` | `POST /v1/chat/completions`，OpenAI shape | OpenAI、DeepSeek、Moonshot/Kimi、Qwen、Zhipu、xAI、Groq、Mistral、Together、Fireworks、DeepInfra、Cerebras、Perplexity、OpenRouter、Ollama …… |
| `CodexResponses` | `POST /v1/responses`，OpenAI Responses API | OpenAI gpt-5、o1/o3/o4 reasoning 系列（含 server-side `web_search`） |
| `GeminiCodeAssist` | Google Cloud Code Assist 内部协议 | Gemini 1.5 / 2.0 / 2.5（OAuth 模式） |

每种协议一份 streaming handler。entry point 都是
`stream_chat_completion(provider, messages, tools) -> SSE Stream`，
具体内部分流到不同协议。

## Tool 调用映射

LLM 调工具的协议跨厂商也不统一：

- **OpenAI ChatCompletions**: `tool_calls: [{id, function: {name, arguments}}]`
- **OpenAI Responses**: `output_item.added` event with `type: function_call`
- **Gemini**: `functionCall: {name, args}` inside `parts`

sidecar 在 `parse_*_tool_call_deltas` 里把每种 shape 归一化成
`ProviderToolCall { id, name, arguments }`，下游就只看到一套形状。
反方向（把 tool result 塞回 LLM）也对应有 3 套渲染逻辑。

## 加新 provider / 新协议

- 加新的 ChatCompletions 兼容厂商：只需 admin catalog 加一行
  + provider id 加路由 case，零额外协议代码——见
  [加一个 model provider](../extension-guides/03-add-a-provider.md)。
- 全新协议（比如 Anthropic Messages API）：需要新增 `ProviderProtocol`
  枚举值 + 对应 streaming handler。
