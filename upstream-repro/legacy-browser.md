# Chromium 109 上导入备份、发送消息失败

## 问题

chat-demo v0.1.3 在 Chromium 109 上会出现两个看起来无关的问题：

- 在设置里导入一份有效的备份 ZIP，界面提示文件格式错误；
- 新建会话发送一句纯文本，界面提示上传失败，实际没有发出聊天请求。

两个问题有同一个原因：代码调用了两个 Chromium 109 还没有提供的数组方法。

修复只替换这两处调用，不改变其他逻辑。

## 用户会看到什么

**导入备份**

选择有效的 `synthetic-one-session.zip` 后，界面提示文件格式错误或导出版本过旧。刷新后会话数量仍为 0。

**发送消息**

即使消息里没有附件，点击发送后也会提示上传失败。浏览器网络面板里没有 `/messages` 请求。

## 最小复现

准备：

- Chromium 109.0.5414.46
- chat-demo v0.1.3 的构建产物
- 本目录的 [`fixtures/synthetic-one-session.zip`](./fixtures/synthetic-one-session.zip)
- 一个可用的 API Key（发送消息需要）

步骤：

1. 用 Chromium 109 打开原版。
2. 打开“设置 → 数据管理”，导入 `synthetic-one-session.zip`。
3. 确认导入。界面应提示格式错误，刷新后没有会话。
4. 在设置里配置 API Key，新建会话，发送 `你好`。
5. 打开浏览器网络面板，确认没有 `/messages` 请求，页面显示上传失败。

修复版应表现为：

- 导入成功，显示 1 个会话、2 条消息；
- 发送产生 1 次 `/messages` 请求，并正常显示和保存回复。

## 原因

两个入口分别调用了：

```ts
// src/services/chat/history/toLocal.ts
file.messages.toSorted(...)

// src/services/chat/store.ts
getContextRounds(request.history).toReversed()
```

`Array.prototype.toSorted` 和 `Array.prototype.toReversed` 在 Chromium 110 才提供，Chromium 109 中不存在。调用时抛出 `TypeError`，上层分别把它显示成“备份格式错误”和“上传失败”。

## 修复

替换为等价写法：

```ts
// 导入：复制后排序，保留原消息数组
file.messages.slice().sort(...)

// 发送：getContextRounds() 每次返回新数组，反转不会影响调用方
getContextRounds(request.history).reverse()
```

## 验证

| 浏览器 | 导入备份 | 发送纯文本 |
|---|---|---|
| Chromium 109.0.5414.46 | 成功导入 1 个会话、2 条消息，父子关系正确 | 1 次 `/messages` 请求，回复正常显示和保存 |
| Edge 157.0.4341.60 | 成功 | 1 次 `/messages` 请求，回复正常显示和保存 |

## 影响范围

项目构建目标包含 Chrome/Edge 105+、Firefox 110+ 和 Safari 16+。这两个方法从 Chrome/Edge 110、Firefox 115、Safari 16 起可用。

因此以下环境可能有同样的兼容风险：

- Chrome/Edge 105–109
- Firefox 110–114

本报告直接验证的是 Chromium 109 和 Edge 157。

代码位置：

- [构建目标](https://github.com/deepseek-ai/chat-demo/blob/8ad7b56/rspack.config.ts#L8)
- [导入调用](https://github.com/deepseek-ai/chat-demo/blob/8ad7b56/src/services/chat/history/toLocal.ts#L239)
- [发送调用](https://github.com/deepseek-ai/chat-demo/blob/8ad7b56/src/services/chat/store.ts#L871)

## 可选：自动化复现

如果不想手动操作浏览器，报告目录里有三个 Playwright 脚本：

```text
tools/zip109.py          原版 ZIP 导入
tools/send109.py         原版纯文本发送
tools/verify_branch.py   修复版导入 + 发送
```

它们需要 Windows、Edge、Python 和 `uv`；Chromium 109 可用 `npx --yes playwright@1.29.1 install chromium` 安装。具体命令和原始记录在：

- [原版导入记录](./evidence/browser-stock-import.json)
- [原版发送记录](./evidence/browser-stock-send.json)
- [修复版记录](./evidence/browser-fixed.json)

## 修复分支

https://github.com/YinkaiYu/chat-demo/compare/8ad7b56...ba6d1ec
