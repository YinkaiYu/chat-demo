# 大 PDF 上传成功，发送消息时返回 32k 错误

## 问题

一份 42 页 PDF 能正常上传，但发送消息时，Messages API 返回 HTTP 400，提示输入超过 32,768 tokens，用户看不到回答。

原因是请求里带了 `safety_check`、`title` 或 `tools` 这些扩展字段；只要带其中任意一个，单次输入就会被限制在 32,768 tokens。

修复只在收到这条特定长度错误、且还没有输出内容时，去掉这些字段，用同一组消息和附件引用重试一次。标题另外用短请求生成。

## 用户会看到什么

- 附件上传过程正常，PDF 能出现在输入框里；
- 点击发送后，界面提示输入过长或请求失败；
- 刷新后消息没有回答，文件本身没有丢失。

## 最小复现

准备：

- chat-demo v0.1.3 的构建产物
- 本目录的 [`fixtures/dsh-dense-probe.pdf`](./fixtures/dsh-dense-probe.pdf)（42 页）
- 可用的 API Key
- 浏览器网络面板，建议开启“保留日志”

步骤：

1. 新建会话，上传 `dsh-dense-probe.pdf`，等附件就绪。
2. 发送：

   ```text
   只输出附件原始印刷第 042 页的九位 Page marker。
   ```

3. 在原版中观察请求：

   ```text
   POST /anthropic/v1/files      200
   POST /anthropic/v1/messages   400

   user input too long, 63941 tokens exceeds max 32768 tokens
   ```

4. 在修复版中用新会话重复同样操作，确认第二次请求返回 200 并显示回答。

第 042 页的正确 Page marker 是 `119932668`，逐页真值在 [`fixtures/page-markers.json`](./fixtures/page-markers.json)。

## 为什么会被限制

chat-demo v0.1.3 的普通聊天请求默认附带三个扩展字段：

| 字段 | 作用 |
|---|---|
| `safety_check` | 高等级内容检查 |
| `title` | 根据本轮内容自动生成标题 |
| `tools` | 联网搜索、读取链接 |

带其中任意一个字段时，Messages API 的单次输入上限是 32,768 tokens；不带这些字段时，同一组消息可以通过。

## 修复后的流程

![大 PDF 触发 32k 错误后的请求流程](./assets/long-document-flow.svg)

具体规则：

1. 首次请求仍然按原样发送，包括三个扩展字段。
2. 只有同时满足以下条件才重试：
   - 返回 HTTP 400；
   - 错误包含 `max 32768 tokens`；
   - 还没有收到任何输出内容。
3. 重试使用相同的消息和同一个附件引用，只去掉 `safety_check`、`title`、`tools`；模型和思考设置不变，附件不重新上传。
4. 回答成功后，如果会话还没有标题，再用“提问节选 + 回答节选 + 附件名”发一个短请求生成标题。

普通短消息、其他错误、已经输出内容的请求都不会进入重试。

## 验证结果

| 检查项 | 结果 |
|---|---|
| 上传 42 页 PDF | Files API 200 |
| 原版发送消息 | 400，提示 `63941 tokens exceeds max 32768 tokens` |
| 修复版首次请求 | 400，触发重试 |
| 修复版重试 | 200，回答正常显示并保存 |
| 第 042 页 Page marker | `119932668` |
| 刷新后第 014 页 Page marker | 一次正确：`521154191` |
| 普通短消息 | 只发送 1 次请求 |
| 会话标题 | 由单独的短请求生成并保存 |

补充对照：同一附件、同一问题，基础请求返回 200；分别只加回高等级检查、自动标题、读取链接或联网搜索，四次都返回 400（48,726 tokens）。这说明限制由这些扩展字段触发，而不是 PDF 文件本身太大。

## 取舍

重试那一次使用 API 默认的内容检查，不启用联网搜索、链接阅读和高等级安全检查；后续消息恢复常规配置。

如果项目要求每次请求都保留高等级安全检查，这个自动重试可能需要调整，或者让用户显式选择。这个取舍不影响 Chromium 109 兼容修复，两项可以分开处理。

## 验证范围

- 两次完成上传的测试都答对了第 042 页。
- 刷新后追问第 014 页，一次得到正确值，另一次回答该页缺失；两次都引用同一会话里的同一个文件。PDF 页面解析由服务端完成，这不在重试逻辑的控制范围内。
- 另有一次上传阶段返回 502，那次没有发送 Messages 请求。

## 请求记录

- [原版 400 记录](./evidence/long-original.json)
- [修复版成功记录](./evidence/long-success.json)
- [四次单字段对照](./evidence/single-option-controls.json)
- [普通短消息记录](./evidence/short-control.json)
- [第 014 页未命中记录](./evidence/long-page14-miss.json)
- [上传 502 记录](./evidence/long-upload-502.json)

## 修复分支

https://github.com/YinkaiYu/chat-demo/compare/8ad7b56...7f28377
