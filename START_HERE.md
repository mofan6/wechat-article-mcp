# 从这里开始

把整个压缩包发给另一台电脑上的 Agent，并告诉它：

> 我使用 Codex 桌面版。请解压，阅读 CODEX_DESKTOP.md、AGENTS.md 和 README.md，安装并接入这个 stdio MCP。运行 bootstrap.py --register-codex 完成安装自检、备份并合并 Codex config.toml；已有 Edge/Chrome 时加 --skip-browser。使用本机微信会话；完成后提醒我重启 MCP/Codex，再调用 doctor 验证。

包里有 5 个工具：环境检查、导入本地微信会话、读取文章、提取阅读/分享/点赞数、导出 Markdown/PDF。

首次安装需要 Python 3.11+ 与互联网；Windows 可复用已安装的 Edge/Chrome。登录/验证码由用户手动完成。去广告由 Agent 查看正文和图片后选择，支持保留数据并剔除同段中的推销文字。

没有打包你的微信凭据、历史文章、爬虫数据库或电脑私有路径。这个包不包含合集 Excel 批量导出。
