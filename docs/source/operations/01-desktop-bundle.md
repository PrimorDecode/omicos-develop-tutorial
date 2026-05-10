# 桌面端打包与签名

发布 release 给最终用户时需要 **签名 + 公证 + 安装**。开发自用可以
跳过签名，清 quarantine 就能跑。

## macOS 签名（Apple Silicon + Intel）

需要：

- Apple Developer ID Application 证书（从 Apple Developer 控制台
  导出 `.p12`）
- 已加入 keychain 的私钥
- App-specific password（用于 notarize）

`src-tauri/tauri.conf.json` 配置：

```json
{
  "tauri": {
    "bundle": {
      "macOS": {
        "signingIdentity": "Developer ID Application: <Your Name> (TEAMID)",
        "providerShortName": "TEAMID",
        "entitlements": "entitlements.plist"
      }
    }
  }
}
```

打包：

```bash
pnpm tauri build
# 自动签名 → 自动 codesign verify → 自动 notarize（如果配了
#  APPLE_ID + APPLE_PASSWORD + APPLE_TEAM_ID env）
```

## entitlements.plist

OmicOS 需要的 entitlements：

```xml
<plist version="1.0">
<dict>
  <!-- sidecar 拉子进程 -->
  <key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
  <!-- 网络（LLM 调用） -->
  <key>com.apple.security.network.client</key><true/>
  <key>com.apple.security.network.server</key><true/>
  <!-- 文件（用户工作区） -->
  <key>com.apple.security.files.user-selected.read-write</key><true/>
</dict>
</plist>
```

最少集合——任何加项都让 review 风险变高。

## Linux

`.AppImage` 自带——`appimagetool` 在 CI 上跑。包到 `.deb` 用
Tauri config 的 `bundle.deb`。Linux 没有 codesign 的概念，但
checksums + GPG signature 推荐做。

## Windows

`.msi` + `.exe` 经 `signtool.exe`签。需要 EV 代码签名证书。

## 不签名分发（仅开发）

```bash
# 接收方机器上
xattr -dr com.apple.quarantine ~/Downloads/OmicOS.app
mv ~/Downloads/OmicOS.app /Applications/
```

不要把这条命令写进给最终用户的安装指南——对终端用户应该签名 +
公证后正常 dmg 双击安装。

## 进一步

- [admin 升级](02-admin-upgrade.md)
- [omicos-ui / 编译与打包](../omicos-ui/04-build-and-bundle.md)
