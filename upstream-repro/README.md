# chat-demo v0.1.3 · 两项问题的复现与修复

| 报告 | 原版上的现象 | 候选修复 |
|---|---|---|
| [Chromium 109 的历史导入和消息发送](./legacy-browser.md) | 有效 ZIP 提示格式错误；空会话发纯文本提示上传失败，聊天请求数为零 | [两行兼容改动](https://github.com/YinkaiYu/chat-demo/compare/8ad7b56...ba6d1ec) |
| [42 页 PDF 上传成功后，提问返回 HTTP 400](./long-document.md) | Files 接收附件，Messages 提示输入超过 32,768 tokens | [仅对特定长度错误重试](https://github.com/YinkaiYu/chat-demo/compare/8ad7b56...7f28377) |

两项修复都从 `v0.1.3`（`8ad7b56`）单独开发。浏览器兼容性可离线验证。长文档实测使用真实接口，重试当轮改用 API 默认内容检查，并停用联网搜索和链接阅读，这一点需要部署方评估。

## 运行原版

下载并解压 [v0.1.3 发布 ZIP](https://github.com/deepseek-ai/chat-demo/releases/download/v0.1.3/chat-demo-v0.1.3.zip)。在含 `index.html` 的目录运行下面的命令，用测试浏览器打开 `http://127.0.0.1:8090/`。手动发送消息前，在设置里配置 API Key。历史导入会覆盖现有会话，请使用空白测试配置。

```sh
python -m http.server 8090 --bind 127.0.0.1
```

## 获取样本和脚本

两篇报告都链接了各自的小样本和逐项记录。要在本机运行脚本，可一次取齐：

```sh
git clone --depth 1 --branch docs/upstream-repro https://github.com/YinkaiYu/chat-demo.git chat-demo-reports
cd chat-demo-reports/upstream-repro
```

## 构建修复版

从 fork 分别检出 `fix/legacy-browser-array-methods` 或 `fix/long-document-retry`。例如，在与报告目录并列的工作目录执行：

```sh
git clone --branch fix/legacy-browser-array-methods https://github.com/YinkaiYu/chat-demo.git chat-demo-compat
```

在对应检出的根目录使用 Node.js 22.12+ 和 pnpm，运行 `pnpm install --frozen-lockfile`。POSIX shell 下运行 `pnpm build`；Windows PowerShell 下分别运行 `$env:NODE_ENV='production'` 和 `pnpm exec rspack build -c rspack.config.ts`。在生成的 `dist` 内启动同样的本地服务器，换一个端口（如 8091），让原版与修复版拥有独立的浏览器存储。
