# WeChat Article MCP

**Designed By MOTAN**

[![Tests](https://github.com/mofan6/wechat-article-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/mofan6/wechat-article-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://www.python.org/)

微信文章保存为 Markdown 与 PDF，让 Agent 在导出前审查正文和图片、去除广告，并提取阅读量、分享量与拇指点赞数。

**[下载最新版安装包](https://github.com/mofan6/wechat-article-mcp/releases/latest)** · [Codex 桌面版接入](CODEX_DESKTOP.md) · [Agent 使用说明](AGENTS.md) · [验证记录](VALIDATION.md)

它是标准 stdio MCP 服务，首次安装需要 Python 3.11+ 和互联网。Codex 接入时安装脚本会先执行连接与 PDF 导出自检，再备份并合并 TOML 配置。微信登录/验证需要在使用者自己的电脑上完成，精简版的保留内容由 Agent 审查后选择。

将微信公众号文章导出为 Markdown（配套本地图片）和 PDF。独立运行，不依赖 Codex、wechat-pcspider、PostgreSQL、抓包证书或发送方的电脑路径。

**对方使用 Codex 桌面版时，先读 CODEX_DESKTOP.md。** 运行 `python bootstrap.py --skip-browser --register-codex`（已有 Edge/Chrome 时）即可执行安装、真实 MCP 自检、配置备份与合并。Codex 使用 config.toml，不使用下面的通用 mcpServers JSON 示例。

## 给另一台电脑上的 Agent

把此目录的压缩包发送过去，让对方 Agent 解压后读 `AGENTS.md` 和本文，再执行安装并注册 MCP。你可以直接发送这句话：

> 请解压这个微信文章导出 MCP 包，阅读 AGENTS.md 和 README.md，检查 Python，运行 bootstrap.py，合并生成的 mcp-config.json 到你的 MCP 配置，并调用 doctor 验证接入。不要覆盖原有配置。登录态使用本机微信，遇到验证让我手动完成。

MCP 宿主必须支持本地 stdio 服务。只有网页聊天、不能启动本地进程的 Agent，不能仅凭压缩包接入。初次安装需要 Python 3.11+ 与互联网；这是可搬运源码安装包，不是含 Python 和浏览器的离线二进制安装器。

## 安装

Windows 在解压目录运行：

```powershell
python bootstrap.py --skip-browser
```

已有 Edge/Chrome 时上面的命令通常够用。否则运行完整安装：

```powershell
python bootstrap.py
```

也提供 `setup.ps1` 入口，不要求更改系统执行策略。macOS/Linux：

```sh
python3 bootstrap.py
```

Linux 需要 Chromium 系统库与中文字体。缺失时按 Playwright 官方安装说明安装：`.venv/bin/python -m playwright install --with-deps chromium`。系统依赖的安装可能需要管理员权限；字体可使用 Noto CJK。Windows 默认使用微软雅黑，macOS 使用苹方。

安装后生成当前电脑的 `mcp-config.json`，把 `mcpServers.wechat-article-export` 合并到宿主配置，不要把其他已有服务器删掉。模板结构：

```json
{
  "mcpServers": {
    "wechat-article-export": {
      "command": "<解压目录>/.venv/Scripts/python.exe",
      "args": ["<解压目录>/server.py"],
      "env": {"PYTHONUTF8": "1", "WECHAT_MCP_OUTPUT_DIR": "<输出目录>"}
    }
  }
}
```

macOS/Linux 的解释器改成 `.venv/bin/python`。配置使用绝对路径，搬动解压目录后重新运行 bootstrap.py 生成配置。宿主字段不是 mcpServers 时，按其文档填写相同的 command/args/env。启动后进程等待标准输入，这是 stdio MCP 的正常状态。

文章图片较多时工具调用可能超过一分钟。若宿主支持请求超时设置，请把本 MCP 的工具调用超时设为至少 300 秒。安装包锁定经过测试的直接依赖版本，之后需要升级时先运行测试。

## 工具

| 工具 | 作用 |
| --- | --- |
| doctor | 检查解释器、PDF 浏览器、输出目录和会话是否配置 |
| import_wechat_session | 从本地 UTF-8 文件导入本机微信文章登录参数 |
| inspect_article | 获取正文、缓存图片，返回文章 ID、正文块和图片路径 |
| get_article_stats | 获取缓存页面的阅读量、分享量、拇指点赞量；缺失为 null |
| export_article | 根据保留/排除块 ID 导出 Markdown/PDF |

例子：先 inspect_article，拿到真实 article_id，再调用：

```json
{"article_id":"<inspect 返回的 ID>","formats":["markdown","pdf"]}
```

精简版由 Agent 查看文字与图片后指定保留块，例如：

```json
{"article_id":"<真实 ID>","keep_block_ids":["b0008","b0009","b0010"],"label":"精简版"}
```

示例块 ID 不代表任何真实文章。每次 inspect 会产生独立缓存和 ID，不能跨文章复用筛选规则。保持内容顺序，不论 ID 参数传入顺序如何。

如果一个段落同时包含有用建议与课程推销，可使用 `text_overrides` 参数，例如 `{"b0012":"该段落去掉推销后保留的纯文本"}`；这会同时作用于 PDF 和 Markdown。不能改写或编造原文数字；图表块不能用文字覆盖。原始缓存保持不变。

## 微信会话与验证

部分文章可直接读取；出现 AUTH_REQUIRED 时，需要本机已登录微信浏览器里的完整文章地址（包含 key、uin，通常也有 pass_ticket）。普通分享短链接不包含这些信息。

把完整地址保存为 UTF-8 本地文件，内容为一行 URL，或 `{"url":"完整地址"}`，再调用 import_wechat_session 指定文件绝对路径。服务只返回导入状态，不返回凭据；导出文件中的链接会去除会话参数。会话过期后重新导入。不要把带凭据的 URL 放到聊天消息或发给别人。

本服务不自动登录微信，不操控客户端，不解密微信聊天库，不安装代理/根证书，也不自动完成验证码。宿主可以在自己的已授权浏览器/电脑操作能力中读取文章地址；没有这些能力时需要用户提供本地文件。RATE_LIMITED 时停止并等待，不能换身份绕过限制。

## 输出与清理

默认写到解压目录的 `exports/`，每次导出独立文件夹，包含 PDF、Markdown、images/、export-info.json。用 WECHAT_MCP_OUTPUT_DIR 可改为桌面或其他路径。WECHAT_MCP_STATE_DIR 可设置缓存目录，WECHAT_MCP_BROWSER 可指定 Edge/Chrome/Chromium 可执行文件。

网络图片只接受 WeChat 常见域名，不支持任意站点。图片下载失败时 inspect 会报告；如果选中了失败图片，export 会返回 MISSING_IMAGES，不会悄悄丢图。PDF 失败时可能已经完成 Markdown，partial_outputs 会报告部分成果。

去广告需要 Agent 审查。工具提供的 ad_review_candidate 是粗略提示，不是图像广告识别器。图表内的原始水印不自动去除。含 rowspan/colspan 的复杂网页表格，Markdown 可能不能完整表达合并单元格，PDF 中保留 HTML 表格结构；文章中以图片形式呈现的表格会保留为图片。视频、音频与动态交互不导出，只导出可读取文字和图片。

## 运行测试

```powershell
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe tests/smoke_mcp.py
```

单元测试使用小型自造文章，验证链接脱敏、保留块筛选、图像失败和空数据语义。smoke 测试启动真实 MCP 子进程，进行 initialize / list_tools / call_tool，并生成小型 Markdown/PDF，验证标准协议与独立工作目录启动。无需微信凭据或外网。

技术依据：[官方 MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)（包固定使用兼容 v1 的 SDK API）、[Playwright Python](https://playwright.dev/python/docs/intro)。测试详情见 VALIDATION.md。

## 开发与许可证

欢迎通过 Issues 报告问题。请说明操作系统、Python 版本、doctor 返回结果及错误代码；不要上传微信登录参数、会话文件或私人文章缓存。

项目使用 [MIT License](LICENSE)。该许可证仅适用于本项目代码，不授予对导出文章、图表或公众号内容的权利。

**Designed By MOTAN**
