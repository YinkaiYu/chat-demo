# chat-demo v0.1.3 的两个问题与修复

| 问题 | 用户看到什么 | 修复 |
|---|---|---|
| [Chromium 109 上导入备份、发送消息失败](./legacy-browser.md) | 导入有效 ZIP 提示格式错误；发送纯文本提示上传失败，实际没有发出聊天请求 | 两行兼容改动 |
| [大 PDF 上传成功，发送消息时返回 32k 错误](./long-document.md) | PDF 已经上传成功，但发送消息时提示输入超过 32,768 tokens，看不到回答 | 只对这条特定错误重试一次 |

两项修复都基于 `v0.1.3`（commit `8ad7b56`），可以分别评估、分别合入。

建议优先评估 Chromium 109 兼容性：只改两行，修复的是构建目标与实际 API 之间的矛盾。

## 运行原版

1. 下载并解压 [v0.1.3 发布包](https://github.com/deepseek-ai/chat-demo/releases/download/v0.1.3/chat-demo-v0.1.3.zip)。
2. 在含 `index.html` 的目录启动本地服务：

```sh
python -m http.server 8090 --bind 127.0.0.1
```

3. 用浏览器打开 `http://127.0.0.1:8090/`。
4. 发送消息前，在设置里配置 API Key。
5. 导入历史会覆盖当前浏览器里的会话，测试时请使用空白浏览器配置。

## 样本和证据

两篇报告各自链接了最小样本、请求记录和脚本。需要一次取齐时：

```sh
git clone --depth 1 --branch docs/upstream-repro https://github.com/YinkaiYu/chat-demo.git chat-demo-reports
cd chat-demo-reports/upstream-repro
```

## 构建修复版

从 fork 检出对应分支：

```sh
git clone --branch fix/legacy-browser-array-methods https://github.com/YinkaiYu/chat-demo.git chat-demo-compat
```

或：

```sh
git clone --branch fix/long-document-retry https://github.com/YinkaiYu/chat-demo.git chat-demo-lo
```

在对应目录使用 Node.js 22.12+ 和 pnpm：

```sh
pnpm install --frozen-lockfile
pnpm build
```

Windows PowerShell 下可以用：

```powershell
$env:NODE_ENV = 'production'
pnpm exec rspack build -c rspack.config.ts
```

构建后把 `dist` 用另一个端口启动，例如 `8091`，避免和原版共用浏览器存储。
