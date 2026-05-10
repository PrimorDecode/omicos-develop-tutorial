# PR 模板

每个 PR 应该自洽——读 PR description 就该能理解动机、改动、影响。

## 模板

```markdown
## Why

<一段话讲为什么需要这个改动。最好包括：>
<- 用户痛点 / 触发的 bug>
<- 之前是怎么做的 / 为什么不够>
<- 这个改动如何解决>

## What

<分点列出实际改动的文件 / 函数 / 行为：>

* `src/foo.rs` — <一句话描述>
* `src/bar.rs` — <...>
* tests/foo.rs` — +N 行新测试

## Verification

- [x] `cargo test --lib` → N/N pass
- [x] `cargo clippy --tests` → no warnings
- [ ] Manual after merge: <具体场景>

## Notes for reviewer

<可选：reviewer 应该重点看哪儿、有什么 trade-off、留待 follow-up>
```

## 字数 / 风格

- title ≤ 70 字符。短句，能从 git log -- oneline 看出做了啥。
- description 没有最大限制，但**单一 concern**——不要在一个 PR 里
  混"加 feature + 不相关 cleanup"
- 不写"AI 生成"宣传词；末尾按需加 `Co-Authored-By:` 标记是 OK 的

## screenshots / 视频

UI 相关 PR **必带** before/after 截图。`<details>` 折叠避免 PR
description 太长。

## CI 失败时

如果 CI 出红：

1. 在 PR 留 comment 解释**为什么红**（机器问题 vs 真 bug）
2. 如果是 bug——修，不要 admin merge 绕过
3. 如果是 infra（GitHub Actions billing 等）——admin merge 时在
   description 写明 fallback 验证（本地 cargo test 通过等）

## 一些反模式

- ❌ "Refactoring + feature in one PR"
- ❌ "Fixes everything!" 几百行 diff
- ❌ Description 只写 "fix bug"，不说哪个 bug
- ❌ Snapshot test 大量更新但没解释为什么

## 进一步

- [Git workflow](01-git-workflow.md)
- [Style + tests](02-style-and-tests.md)
