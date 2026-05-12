# 移动 / Web SPA（omicos-server-ui）

`omicos-server-ui` 是跑在 `auth.omicverse.com` 的 Vue 3 SPA + 同一份
代码用 Capacitor 7 wrap 成的 iOS app。它不是桌面 Tauri 端的替代品，
而是**云端伴侣**——让用户和实验室成员能在任意设备上：

- 查看自己跑过的 conversation 历史
- 浏览自己留下的 trajectory（runbook）
- 给别人的 trajectory 留言 / 问 LLM 问题
- 看实验室成员的工作（mentor / 学生互相可见）

源码：[`omicos-server-ui`](https://github.com/PrimorDecode/omicos-server-ui)。
服务端是 [`omicOS-server`](https://github.com/PrimorDecode/omicOS-server)。

## 架构层次

```
┌─────────────────────────────────────────┐
│ Capacitor wrap (iOS)                    │
│  - capacitor:// scheme                  │
│  - native back-button, status-bar       │
└──────────────────┬──────────────────────┘
                   │ WebView
┌──────────────────▼──────────────────────┐
│ Vue 3 SPA (IndexView.vue 单文件巨集)    │
│  ├─ IndexedDB v3 (conv / traj / disc)   │
│  ├─ Auth.js (cookie 派生)               │
│  ├─ WS /ws/events                       │
│  ├─ visualViewport composer dock        │
│  └─ i18n (en / zh)                      │
└──────────────────┬──────────────────────┘
                   │ HTTPS + WSS
                   ▼
            auth.omicverse.com
        (omicOS-server, Flask + async)
```

## 三个核心模块

```{admonition} Profile tab 已经替换为 Groups（PR #102）
:class: warning

2026-05 起底部 tabbar 没有 "Profile" 这一项了——`Profile` 被
`Groups` 替换。个人信息（头像、订阅）挪到右上角 kebab → 用户菜单。
旧版本写的 deeplink `#profile` 现在重定向到 `#groups`。
```

### Chat — 对话同步

- 列表入口：底部 tabbar `Chat`
- 数据：`omicOS-server` 的 `/api/processes` + `/api/processes/{pid}/conversations/{sid}`
- 同步：WebSocket `/ws/events` 推 `process_updated`，SPA 收到后用
  `?since_seq=<last_seq>` 增量 catch up
- 离线：IndexedDB store `conversations` 持久化全量，启动时立刻显示
  cache、后台 catch up

### Trajectory — 长任务回放

- 列表入口：底部 tabbar `Trajectory`
- 列表按时间分组：今天 / 本周 / 本月 / 历史月份（PR #101）
- 详情页 2026-05 完全重写（v2 设计，PR #117-#120）：
  - 扁平 section（无 card chrome），节标题用 i18n
  - 内联 SVG 图标取代 emoji
  - 底部贴 Stats strip（records / tools / errors）
  - AI 总结栏只显示 "AI 总结 · <时间>"，不带模型名
- Owner-only 视图：
  - "讨论记录" sheet —— 谁问过你什么（PR #111）
  - 桌面端隐藏 Composer + Process 工具栏（PR #115）

### Groups — 三级钻取（lab → 成员 → 该成员的 trajectory）

- 入口：底部 tabbar `Groups`
- 三级页面层级：
  1. Lab 列表（你加入的所有 lab）
  2. Lab 详情：成员列表 + 该 lab 内每位成员的近期 trajectory 段落
  3. 点某条 trajectory → 跳进 Trajectory 详情页（back 按钮回到刚才的
     lab 详情位置，不会丢失上下文，见 PR #110）

## Trajectory Q&A —— 两条 sheet

### Viewer 提问（PR omicOS-server #63 + UI #103）

任何能看到一条 trajectory 的用户都能在右下角点 💬 打开 Q&A sheet：

- iOS bottom-sheet 样式，滚动 chat
- 调 `POST /api/trajectories/{sid}/discuss` body `{messages: [...]}`
- LLM 读这条 trajectory 的缓存 summary + 问题 → 回答
- viewer 的提问 + LLM 回答都持久化到服务端（owner 自己提问的不算
  "discussion" 也不入审计）
- 本地 IndexedDB `trajectory_discussions` 存 viewer 自己的 Q&A 历史
  做 offline-first

### Owner 审计（PR omicOS-server #65 + UI #111、#112）

owner 在自己 trajectory 的右上角能打开"讨论记录" sheet：

- 列表显示**所有 viewer × 主题**，按最近时间排序
- 点进某 viewer 看完整对话
- 配合 `last_discussion_at` 字段做未读小红点（PR omicos-server-ui #114）

## IndexedDB v3

PR omicos-server-ui #116 + 服务端 PR #60：

```js
indexedDB.open('omicos-spa-v1', 3);
```

三个 store：

- `conversations` (keyPath `session_id`, `last_seq`) — chat 历史 + 游标
- `trajectories` (keyPath `session_id`) — trajectory records 缓存
- `trajectory_discussions` (keyPath `session_id`) — viewer-local Q&A 历史

v2 → v3 升级时容易卡住——另一个开着 v2 连接的 tab 会**阻塞**升级，
old API 没回调任何东西，浏览器静默卡住。修复：

- 3 秒 `setTimeout` 兜底 reject（不让 UI 永久白屏）
- 注册 `onblocked` 监听 console.warn

## Capacitor 适配

- SPA 用 `<base href="/">` + `vue-router` history mode；iOS 壳子
  内 origin 是 `capacitor://localhost`
- 所有 `/api`、`/admin`、`/ws` 前缀的请求被 prepend 成
  `https://auth.omicverse.com/api/...`
- CORS：`omicOS-server` PR #61 把 `capacitor://localhost`、
  `ionic://localhost`、`https://localhost` 都加进白名单

## composer 软键盘对接

PR omicos-server-ui #97。**不引入 Capacitor 插件**，直接走标准
`window.visualViewport` API：

```js
window.visualViewport.addEventListener('resize', () => {
  const keyboardH = window.innerHeight - window.visualViewport.height;
  composer.style.transform = `translateY(${-keyboardH}px)`;
});
```

iOS Safari + Capacitor WebView 都原生支持，比 plugin 路径稳定。

## i18n

`src/i18n.ts` 维护 en / zh 两张表，组件用 `t('key')` 取词。
trajectory section 标题 / Q&A 提示 / AI 总结栏文案全部走 i18n
（PR #119）。**中文用户看到纯中文，不双语混写**——这是 2026-05
专门修过的（之前是 "Q&A clusters · 问答聚类" 这种混排，用户嫌乱）。

## 部署

```bash
cd omicos-server-ui
npm run build          # 产 dist/
./scripts/deploy.sh    # rsync dist/ → root@23.226.134.91:/var/www/omicos-server-ui/
                       # 后端 nginx 直接 serve；iOS 端 cap sync + xcodebuild
```

桌面浏览器直接访问 `https://auth.omicverse.com/`，iOS 通过 TestFlight
分发。强退重开 app 后 SPA 拉新 bundle（无 force-update 机制，靠
HTTP cache）。

## 进一步

- [Cloud sync](../concepts/05-cloud-sync.md) — conversation cursor + WS push 在底层是怎么走的
- [Trajectory 数据布局](../omicos-admin/01-data-layout.md) — 服务端的存储 schema
