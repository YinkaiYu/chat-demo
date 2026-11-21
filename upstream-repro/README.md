# chat-demo 的两项兼容性修复

这两个问题是独立的，可以分别评估、分别合入。

建议先看 **Chromium 109 兼容性**：它只改两行，修复的是构建目标与实际 API 的矛盾，风险很低。

## 报告

1. [Chromium 109：有效备份无法导入，发送消息提示上传失败](./legacy-browser.md)
2. [大 PDF：发送消息时被 32k 限制拒绝](./long-document.md)

## 代码分支

- `fix/legacy-browser-array-methods`  
  https://github.com/YinkaiYu/chat-demo/compare/8ad7b56...ba6d1ec
- `fix/long-document-retry`  
  https://github.com/YinkaiYu/chat-demo/compare/8ad7b56...7f28377

两个分支都基于 `v0.1.3`（`8ad7b56`），没有新增依赖，通过 `pnpm type`、`pnpm lint`、`pnpm build`。

## 复现文件

- [`fixtures/synthetic-one-session.zip`](./fixtures/synthetic-one-session.zip)
- [`fixtures/dsh-dense-probe.pdf`](./fixtures/dsh-dense-probe.pdf)
- [`fixtures/page-markers.json`](./fixtures/page-markers.json)
