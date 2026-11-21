# Chromium 109：有效备份无法导入，发送消息提示上传失败

## 一句话说明

`chat-demo v0.1.3` 在 Chromium 109（以及构建目标声明支持的 Chrome/Edge 105–109、Firefox 110–114）上调用浏览器尚未提供的两个数组方法，导致两个看起来无关、实际同源的问题：

- 设置里导入有效的备份 ZIP，界面误报备份格式错误
- 新会话发送一条纯文本，界面提示上传失败，实际没有发出 Messages 请求

修复只改两行，把两个新方法替换为等价写法，不改变行为。

## 影响范围

`rspack.config.ts` 声明的构建目标是：

```ts
const targets = ['chrome >= 105', 'edge >= 105', 'safari >= 16', 'firefox >= 110']
```

这段配置会传给 SWC 的 `env.targets`，即项目声明支持这些浏览器。

`chat-demo v0.1.3` 使用的两个方法，浏览器支持时间晚于声明目标：

| 方法 | Chrome / Edge | Firefox | Safari |
|---|---|---|---|
| `Array.prototype.toSorted` | 110 | 115 | 16 |
| `Array.prototype.toReversed` | 110 | 115 | 16 |

因此，Chrome/Edge 105–109、Firefox 110–114 都可能在对应路径上报错。Safari 16 不受影响。

参考资料：

- [MDN: Array.prototype.toSorted](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Array/toSorted)
- [MDN: Array.prototype.toReversed](https://developer.mozilla.org/docs/Web/JavaScript/Reference/Global_Objects/Array/toReversed)

## 两个问题的具体位置

### 问题 1：导入有效 ZIP 被误报格式错误

代码位置：

- `src/services/chat/history/toLocal.ts`

```ts
const sorted = file.messages.toSorted((a, b) => a.id - b.id)
```

在 Chromium 109 中，`file.messages.toSorted` 是 `undefined`，调用时抛出 `TypeError`。导入流程把异常当成归档格式错误处理，用户看到的是“备份格式错误/无法导入”。

### 问题 2：发送纯文本提示上传失败

代码位置：

- `src/services/chat/store.ts`

```ts
for (const [user] of getContextRounds(request.history).toReversed()) {
```

在 Chromium 109 中，`Array.prototype.toReversed` 不存在，发送流程在准备附件阶段抛错。虽然本次消息没有附件，界面仍显示“上传失败”，且实际没有发出 Messages 请求。

## 最小复现

准备：

- Chromium 109 浏览器（测试版本：109.0.5414.46）
- `v0.1.3` 的构建产物
- 本目录的 [`fixtures/synthetic-one-session.zip`](./fixtures/synthetic-one-session.zip)

步骤：

1. 用 Chromium 109 打开 `v0.1.3` 构建产物。
2. 打开“设置 → 数据管理”，导入 `synthetic-one-session.zip`。
3. 观察结果：界面报备份格式错误，导入没有完成。
4. 新建会话，输入 `你好` 并发送。
5. 观察结果：界面显示上传失败，网络面板中没有 `/messages` 请求。

预期：

- 导入成功，1 个会话、2 条消息
- 发送产生 1 次 `/messages` 请求，并正常显示回复

实际：

- 导入报格式错误
- 发送只显示上传失败，请求数为 0

## 修复方式

只替换调用，不改变逻辑：

```ts
// 导入：复制数组后排序
const sorted = file.messages.slice().sort((a, b) => a.id - b.id)

// 发送：反转刚创建的轮次数组
for (const [user] of getContextRounds(request.history).reverse()) {
```

`getContextRounds()` 每次返回新数组，因此 `reverse()` 不会修改调用方持有的历史数据，遍历顺序保持不变。

## 验证结果

| 浏览器 | 导入 | 发送 |
|---|---|---|
| Chromium 109.0.5414.46 | 成功，1 个会话 / 2 条消息，父子关系正确 | 1 次 POST，正常显示并保存回复 |
| Edge 157.0.4341.60 | 成功 | 1 次 POST，正常显示并保存回复 |

## 建议

这是与构建目标直接矛盾的兼容性问题，修复只改两行，没有行为变化。**建议至少先接收这一项。**

分支：`fix/legacy-browser-array-methods`  
对比：https://github.com/YinkaiYu/chat-demo/compare/8ad7b56...ba6d1ec
