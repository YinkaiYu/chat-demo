# Chromium 109 无法导入有效备份，也无法发送普通消息

官方 v0.1.3 在真实 Chromium 109.0.5414.46 上有两个独立入口会失败。两处都调用了该引擎缺少的数组方法。修复仅替换这两个调用。[两行代码差异](https://github.com/YinkaiYu/chat-demo/compare/8ad7b56...ba6d1ec)

## 手动复现

按[运行说明](./README.md)打开原版，使用空白测试配置。下载 [1,388 字节的合成 ZIP](./fixtures/synthetic-one-session.zip)，保留 ZIP 格式。

| 操作 | 原版 Chromium 109 | 修复版 Chromium 109 |
|---|---|---|
| 设置 → 数据管理 → 上传 → 选中 ZIP → 在页面点击「确认导入」 | 提示文件格式错误或导出版本过旧；刷新后会话数为 0 | 显示「已导入 1 个对话」；刷新后仍有一问一答，父子关系正确 |
| 配置 API Key，新建会话，发送一句纯文本。在网络面板筛选 `/messages` | 页面提示「上传失败」，聊天 POST 请求为 0 次 | 正常发出一次 POST，收到回复后显示并保存 |

导入时，`file.messages.toSorted()` 抛错，界面统一显示了导入失败文案。改为复制后排序可保留原消息数组。发送时，即使没有附件，准备阶段也会调用 `getContextRounds(...).toReversed()`；该函数每次都创建新数组，可直接用 `reverse()` 保持原遍历顺序。[导入调用](https://github.com/deepseek-ai/chat-demo/blob/8ad7b56/src/services/chat/history/toLocal.ts#L239) · [发送调用](https://github.com/deepseek-ai/chat-demo/blob/8ad7b56/src/services/chat/store.ts#L871)

## 离线验证两端

下列脚本不需要账号，以模拟回复记录浏览器实际发出的请求。使用 Windows、已安装的 Edge、Python 和 uv。在依赖和浏览器首次安装完成后即可离线运行。测试使用的 Chromium 109 对应 Playwright revision 1041，可用 `npx --yes playwright@1.29.1 install chromium` 下载。以下命令在本报告目录执行，替换引号中的本机路径。

```text
uv run --with playwright python tools/zip109.py "<原版发布ZIP>" "<Chromium109的chrome.exe>" fixtures/synthetic-one-session.zip
uv run --with playwright python tools/send109.py "<原版解压后含index.html的目录>" "<Chromium109的chrome.exe>"
uv run --with playwright python tools/verify_branch.py "<修复分支构建的dist>" "<Chromium109的chrome.exe>" fixtures/synthetic-one-session.zip
```

前两条在相同引擎、相同输入下，分别比较发布文件与仅在内存中替换相关调用的结果。第三条直接使用提交 `ba6d1ec` 的生产构建；在 Chromium 109 和 Edge 157 上，两项操作均通过。发送测试各观察到一次 POST，模拟回复 `FIXTURE_OK` 写入会话。[原版导入记录](./evidence/browser-stock-import.json) · [原版发送记录](./evidence/browser-stock-send.json) · [最终构建记录](./evidence/browser-fixed.json)

## 影响范围

项目构建目标包含 Chrome/Edge 105+、Firefox 110+ 和 Safari 16+。据 MDN，两种方法均从 Chrome/Edge 110、Firefox 115、Safari 16 起可用。据此推断，Chrome/Edge 105–109 和 Firefox 110–114 存在相应兼容风险；本报告直接验证的浏览器为 Windows Chromium 109 和 Edge 157。[构建配置](https://github.com/deepseek-ai/chat-demo/blob/8ad7b56/rspack.config.ts#L8) · [MDN 兼容数据](https://raw.githubusercontent.com/mdn/browser-compat-data/main/javascript/builtins/Array.json)
