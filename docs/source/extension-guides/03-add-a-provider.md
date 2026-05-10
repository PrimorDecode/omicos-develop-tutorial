# 加一个 model provider

OmicOS 的 provider 路由是 catalog-driven 的——admin 的 `models.json`
说哪个 provider 在哪个 base URL，sidecar 顺着读。绝大多数情况下加
新 provider **不用改任何 Rust 代码**。

## 三类典型场景

### 场景 1：OpenAI ChatCompletions 兼容服务

绝大多数（DeepSeek、Moonshot/Kimi、Qwen、Together、Fireworks、
DeepInfra、Cerebras、Perplexity、OpenRouter、Ollama……）都属于这类。

只需 admin `models.json` 加一项：

```json
{
  "id": "newprov",
  "label": "New Provider",
  "api_base": "https://api.newprov.com/v1",
  "env_var_name": "NEWPROV_API_KEY",
  "models": [
    {"id": "newprov-chat-2025", "label": "NewProv Chat 2025"},
    {"id": "newprov-thinking-2025", "label": "NewProv Reasoning"}
  ]
}
```

客户端 sync → SPA 设置页"Provider"下拉里立刻出现新选项。用户填 API
key（写到 keychain，env var 名字按 `env_var_name` 注入），就能跑。

### 场景 2：Codex Responses API（OpenAI o-series / gpt-5）

`models.json` 里同一个 provider id 下加 reasoning 模型即可，但要
显式标 `protocol: "codex_responses"`：

```json
{"id": "openai", "...": "...",
 "models": [
    {"id": "gpt-5", "protocol": "codex_responses"},
    {"id": "o3", "protocol": "codex_responses"}
 ]
}
```

sidecar 里有专门 handler 跑这个协议（[`providers.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/providers.rs)）。

### 场景 3：全新协议（Anthropic Messages、自家私有）

需要改 Rust：

1. 在 [`providers.rs`](https://github.com/PrimorDecode/omicos-core/blob/main/src/providers.rs)
   的 `ProviderProtocol` 枚举加变体
2. 写对应的 streaming handler `stream_<your_protocol>(...)`
3. 在 `stream_chat_completion` 的派发处加分支
4. 把 tool call 的 deltas 归一化到 `ProviderToolCall`
5. 单测：往 handler 喂一段 fixture SSE，断言结果

历史例子可参考 [Gemini Code Assist 协议的实现](https://github.com/PrimorDecode/omicos-core/blob/main/src/providers.rs)。

## 环境变量约定

| 用途 | 变量名 |
|---|---|
| API key | `<UPPER>_API_KEY`（默认）或 `env_var_name` 显式覆盖 |
| Base URL 临时覆盖 | `OMICOS_PROVIDER_<UPPER>_BASE_URL` |
| 模型默认 temperature | 不再支持（PR #112 移除 temperature 字段） |

## 测试新 provider

```bash
# CLI 模式直接打：
echo '你好' | omicos chat \
    --provider newprov \
    --model newprov-chat-2025

# 或者本地起 sidecar，curl SSE：
curl -N -X POST http://127.0.0.1:<port>/api/chat/stream \
    -H 'content-type: application/json' \
    -d '{"messages": [{"role":"user","content":"你好"}],
         "provider":"newprov","model":"newprov-chat-2025"}'
```

## 进一步

- [Providers 与 Protocols 概念](../concepts/03-providers-and-protocols.md)
- [admin / models.json](../omicos-admin/01-data-layout.md#modelsjson-shape)
