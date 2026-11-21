# 42 页 PDF 上传成功后，提问返回 HTTP 400

在 chat-demo v0.1.3 中，Files 成功接收测试 PDF，随后 Messages 报输入超过 32,768 tokens。同一组消息和文件引用，去掉本次请求的扩展选项后可以完成回答。候选改动仅在收到对应长度错误时自动重试一次。[代码差异](https://github.com/YinkaiYu/chat-demo/compare/8ad7b56...7f28377)

**需要评估的取舍**：重试当轮采用 API 默认内容检查，无法联网搜索或阅读链接。下一轮重新尝试常规配置。要求每轮都做高等级输入和输出检查的部署，需要单独评估这种恢复方式。[DeepSeek 内容安全说明](https://api-docs.deepseek.com/guides/safety/)

## 复现一次首问

1. 按[运行说明](./README.md)打开发布版，新建会话，在设置中配置可调用官方 Files 和 Messages 的 API Key。使用默认模型 `deepseek-flash` 与原版默认设置。打开浏览器网络面板，开启「保留日志」。
2. 上传 [42 页合成 PDF](./fixtures/dsh-dense-probe.pdf)，等附件就绪。发送「查阅附件最后一页。只输出印刷第 042 页 Page marker 后面的九位数字。」
3. 在原版的一次实测中，`POST /anthropic/v1/files` 返回 200，`POST /anthropic/v1/messages` 返回 400，提示 `user input too long, 63941 tokens exceeds max 32768 tokens`。不同上传的 token 数会变化。若原请求直接返回 200，请记录配置与响应；该次没有触发长度重试。[原版记录](./evidence/long-original.json)
4. 在修复版新会话重复步骤。触发错误时，核对下表中的请求顺序。文件只上传一次，回答应完整显示，刷新后可以重开会话。该题的校验码为 `119932668`。[修复版记录](./evidence/long-success.json) · [逐页真值](./fixtures/page-markers.json)

| 修复版同一次会话 | HTTP | 可核对的内容 |
|---|---|---|
| 上传 PDF | 200 | 取得附件引用 |
| 提交原始提问 | 400 | 该次计为 63,947 tokens，最大值为 32,768 |
| 自动重试 | 200 | `messagesHash`、`referenceHashes`、`sharedBodyHash` 一致；省略 `tools`、`title`、`safety_check`；流完成，回答已保存 |
| 尚需自动标题 | 200 | 后台短请求带提问、回答节选及附件名，不含文件引用；标题写入会话 |
| 刷新后追问 | 200 | 使用原附件引用；本次直接以常规配置完成 |

## 触发条件与对照

发送前没有收到内容块、Messages 返回 HTTP 400、且错误符合 `user input too long, <数字> tokens exceeds max 32768 tokens` 时，候选版才使用普通请求重试一次。这个判定适用于各轮。常规请求按设置声明网页工具，自动标题按需启用。标题失败不会撤回已保存的回答。

![测试 PDF 触发长度重试后的请求顺序](./assets/long-document-flow.svg)

在另一组单变量实验中，同一附件、同一问题的基础请求返回 200。分别只加回高等级检查、启用标题、声明阅读链接工具或联网搜索工具，四次均报 48,726 tokens 超出 32,768。这里描述的是这些具体设置的观测结果。普通短问在最终构建上只发送一次。[五次对照](./evidence/single-option-controls.json) · [短问记录](./evidence/short-control.json)

## 文档读取与验证环境

两次完成上传的最终构建测试均答对第 042 页。刷新后追问第 014 页，一次得到正确值 `521154191`，另一次回答该页缺失；两次追问都引用各自会话里的同一文件。另有一次上传阶段返回 502，尚未发送 Messages。请求重试可由网络记录和会话落盘验证，客户端日志不能区分服务端解析与模型作答对漏页的影响。[第 014 页未命中](./evidence/long-page14-miss.json) · [上传 502](./evidence/long-upload-502.json)

真实接口对照使用 Edge，由本机 DSH 账户提供鉴权，保留官方 Files、Messages 路径和请求体。公开分支沿用 demo 自带的 API Key 入口。公开记录为脱敏字段和摘要。实测运行时代码来自 `4357c0d`；到 `7f28377` 的后续两次提交仅改中英文 README。[提交差异](https://github.com/YinkaiYu/chat-demo/compare/4357c0d...7f28377)
