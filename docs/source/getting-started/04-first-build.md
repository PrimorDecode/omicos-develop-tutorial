# 第一次构建与运行

确认 [本地开发环境](03-dev-environment.md) 装完后，跑一次完整的
release 流程：编 sidecar → 拷到 ui binaries → tauri build → 装机。
这是日常合 PR 后的标准动作。

## 完整 5 步

```bash
# 1. 拉 main
cd ~/work/omicverse-project/omicos-core
git checkout main && git pull --ff-only origin main

# 2. release sidecar
cargo build --release
# 产物: target/release/omicos (~21 MB)

# 3. 拷到 ui binaries
cp target/release/omicos \
   ../omicos-ui/src-tauri/binaries/omicos-aarch64-apple-darwin

# 4. tauri 全量打包
cd ../omicos-ui
pnpm tauri build
# 产物: src-tauri/target/release/bundle/macos/OmicOS.app
#      src-tauri/target/release/bundle/dmg/OmicOS_<v>_aarch64.dmg

# 5. 安装到 /Applications
pgrep -f "/Applications/OmicOS.app" | xargs -r kill -9 2>/dev/null
rm -rf /Applications/OmicOS.app
cp -R src-tauri/target/release/bundle/macos/OmicOS.app /Applications/
xattr -dr com.apple.quarantine /Applications/OmicOS.app
```

打开 `OmicOS.app` 验证。

## 平均耗时

| 步骤 | 时间 |
|---|---|
| `cargo build --release` 全量 | 60–120s（增量 < 30s） |
| `pnpm tauri build` 全量 | 90–180s |
| 装机 | < 5s |

## 不打 DMG 的快速路径

DMG bundling 偶尔会卡（codesign 配错、bundle_dmg.sh 报错等）。
**`.app` 已经在前一步生成**，可以直接 `cp -R` 到 `/Applications/`，
跳过 DMG 也能用。

## 环境变量

发布之前可以临时覆盖某些行为：

```bash
# 跑 sidecar 不连 admin 同步
OMICOS_AGENTS_OFFLINE=1 ./target/release/omicos

# 用本地 admin 调试
OMICOS_AGENTS_CLOUD_URL=http://127.0.0.1:5070/api/public/agents \
    ./target/release/omicos

# 加自定义 skill 根
OMICOS_SKILL_ROOTS=/tmp/dev-skills ./target/release/omicos
```

## 验证 sidecar 二进制确实是新的

```bash
stat -f "%Sm %z" /Applications/OmicOS.app/Contents/MacOS/omicos
# 期望 mtime 是你刚刚 cargo build 完的时间
```

如果时间戳没更新，回去检查 step 3 的拷贝路径——`omicos-ui/src-tauri/binaries/`
下面的二进制名必须按平台正确：

| 平台 | 文件名 |
|---|---|
| macOS Apple Silicon | `omicos-aarch64-apple-darwin` |
| macOS Intel | `omicos-x86_64-apple-darwin` |
| Linux | `omicos-x86_64-unknown-linux-gnu` |
| Windows | `omicos-x86_64-pc-windows-msvc.exe` |

## 进一步

- [桌面端打包](../operations/01-desktop-bundle.md) — DMG / 签名 / 公证
- 改 sidecar 后还要改前端 IPC：[omicOS-ui 架构](../omicos-ui/01-architecture.md)
