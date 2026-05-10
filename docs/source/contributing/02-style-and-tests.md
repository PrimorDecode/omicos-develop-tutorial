# 代码风格与测试

## Rust（omicos-core）

格式：`cargo fmt`（标准 rustfmt 配置，无自定义）。
Lint：`cargo clippy --all-targets -- -D warnings`。

风格约定：

- **doc comment 必写**——pub fn / pub struct / pub mod。说**为什么**
  存在（不是 paraphrase 函数名）
- **错误用 `anyhow::Result` + `Context`**——library 层用 `thiserror`
  自定义 error，但跨模块边界回归 anyhow
- **不 panic**——`unwrap()` / `expect()` 只在 setup 阶段（CLI parse、
  fixture），运行时一律 `?`
- **避免无谓 clone**——优先 `&` 引用，trait bounds 写 `impl IntoIterator<Item = ...>`
- **测试就近**——`#[cfg(test)] mod tests` 在文件末尾；跨模块 fixture
  放 `tests/` 目录

测试：

- `cargo test --lib` 单测
- `cargo test --tests` integration
- 集成测试用 fixture，不打真 LLM API
- snapshot 测试用 [`insta`](https://insta.rs/)（按需引入）

## TypeScript（omicos-ui）

格式：Prettier（默认配置 + 单行 ≤ 100）。
Lint：ESLint（`@typescript-eslint`）。

约定：

- **函数式优先**——能用 const arrow 就别用 class
- **state 入 store**——组件级临时 state 用 `ref()`，跨组件用 Pinia
- **类型显式**——public function 总写 return type
- **避免 `any`**——确实需要时用 `unknown` + narrow

测试：

- 组件测试用 [Vitest](https://vitest.dev) + [Vue Test Utils](https://test-utils.vuejs.org/)
- E2E 用 Playwright（少量关键路径）

## Python（omicos-admin）

格式：`black` + `isort`。
Lint：`ruff`。

约定：

- type hint：3.11+ 语法（`list[str]` 而非 `List[str]`，`X | None` 而非
  `Optional[X]`）
- **不暴露 secret 到日志**——必经 mask helper
- 测试用 `pytest`，fixture-based

## Markdown（本仓库 / 文档）

- 中文 / 英文 / 代码混排时**有空格**：`使用 Sphinx 构建` ✓ / `使用Sphinx构建` ✗
- 列表用 `-`，不用 `*`
- 链接用 inline 形式 `[文字](url)`，不用 reference style
- code fence 必标语言（`bash` / `rust` / `python` / ...）

## 进一步

- [Git workflow](01-git-workflow.md)
- [PR 模板](03-pr-template.md)
