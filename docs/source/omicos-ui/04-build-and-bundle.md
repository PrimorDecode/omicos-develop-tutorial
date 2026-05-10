# 编译与打包

## 开发模式

```bash
cd omicos-ui
pnpm install
pnpm tauri dev   # 同时跑 vite + Tauri shell + sidecar
```

Vite HMR 处理前端改动，Rust shell / sidecar 改动需要 Ctrl+C 重启。

## 完整 release 流程

```bash
# 1. 拷一份新的 sidecar 到 binaries/
cp ../omicos-core/target/release/omicos \
   src-tauri/binaries/omicos-aarch64-apple-darwin

# 2. 打包
pnpm tauri build

# 产物：
# src-tauri/target/release/bundle/macos/OmicOS.app
# src-tauri/target/release/bundle/dmg/OmicOS_<v>_aarch64.dmg
```

## 平台差异

| 平台 | sidecar 文件名 | 产物 |
|---|---|---|
| macOS Apple Silicon | `omicos-aarch64-apple-darwin` | `.app` + `.dmg` |
| macOS Intel | `omicos-x86_64-apple-darwin` | `.app` + `.dmg` |
| Linux | `omicos-x86_64-unknown-linux-gnu` | `.AppImage` + `.deb` |
| Windows | `omicos-x86_64-pc-windows-msvc.exe` | `.msi` + `.exe` |

文件名是 Tauri 通过 `target_triple()` 自动选的，错了就找不到 sidecar。

## 内核 venv 也要打包

`src-tauri/binaries/omicos-env/` 里要有完整的 venv 副本。这个目录通过
Tauri config `bundle.resources` 拷进 `.app`。venv 体积大（~500MB），
是 OmicOS bundle 几个 GB 的主要原因。

## 签名 / 公证（macOS）

CI 上才做。本地构建不签名也能跑——清掉 quarantine 即可：

```bash
xattr -dr com.apple.quarantine /Applications/OmicOS.app
```

签名细节见 [桌面端打包](../operations/01-desktop-bundle.md)。

## 进一步

- [桌面端打包 / 签名 / 公证](../operations/01-desktop-bundle.md)
- [第一次构建](../getting-started/04-first-build.md)
