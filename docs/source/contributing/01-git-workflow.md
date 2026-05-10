# Git workflow

OmicOS 项目用一个**严格但简单**的 git workflow：所有改动 → fresh
branch → PR → CI 绿 → squash merge → 删分支。任何"在 main 上直接
push"都不允许（除非紧急 hotfix，并 post-mortem）。

## 一次完整改动

```bash
# 0. 同步 main
git checkout main && git pull --ff-only origin main

# 1. 开新分支
git checkout -b feat/<descriptor>          # 新功能
# or fix/<descriptor>                      # bug fix
# or chore/<descriptor>                    # 杂事
# or docs/<descriptor>                     # 文档

# 2. 写代码 + 测试
# ...
cargo test --lib              # Rust 仓库
pnpm test                     # ui 仓库
make html                     # 文档仓库

# 3. commit
git add <specific-files>      # 不要 git add . / -A
git commit -m "$(cat <<'EOF'
<type>(<scope>): <subject>

<body — 描述为什么改，不是什么>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"

# 4. push + 开 PR
git push -u origin feat/<descriptor>
gh pr create --title "..." --body "..."

# 5. CI 绿后合（管理员或 CI bot）
gh pr merge <num> --squash    # 默认 squash
# 或 --merge 保留 commit 历史（大 feature）

# 6. 清理
git checkout main && git pull --ff-only origin main
git branch -d feat/<descriptor>
git push origin --delete feat/<descriptor>
```

## Commit message 规范

`<type>(<scope>): <subject>` —— 标题：

- **type**：`feat` / `fix` / `refactor` / `docs` / `chore` / `test` /
  `perf`
- **scope**：模块（`agents` / `skills` / `providers` / `runtime` /
  ...）
- **subject**：祈使句、英文、≤ 60 字符

body 写**为什么**而不是**什么**。代码 diff 已经说了"什么"。

## CI 的角色

CI 跑：

- `cargo fmt --check` / `cargo clippy --tests`
- `cargo test --lib` / `cargo test --doc`
- `pnpm test` / `pnpm tauri build`（ui）
- `make linkcheck`（docs）

**CI 不绿不能合**——除非 CI 故障（比如 GitHub Actions billing 之类
账号级问题），按 admin merge 处理并在 PR 备注。

## 不允许的操作

| 操作 | 原因 |
|---|---|
| `git push --force main` | 永远不允许 |
| `git push --no-verify` | 跳 hook = 跳质量门 |
| 在没 review 的情况下 `--admin` merge | 仅 CI 故障时允许 |
| `git rebase -i` 改公共分支 | 重写公共历史 = 协作灾难 |
| `git commit --amend` 已 push 的 commit | 同上 |

## branch protection

main 分支配置：

- 必须 PR 才能合
- 至少 1 reviewer approve
- CI 必须通过
- branch 必须 up-to-date（force update before merge）

## 进一步

- [Style + tests](02-style-and-tests.md)
- [PR 模板](03-pr-template.md)
