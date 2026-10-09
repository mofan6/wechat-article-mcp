# Codex 桌面版接入

本包包含真实 stdio MCP 服务。Codex 桌面版读取 `~/.codex/config.toml` 的 `[mcp_servers.<name>]` 配置；不是把 ZIP 拖进聊天就会自动启用。

给目标电脑上的 Codex 发送：

> 请解压这个包，阅读 CODEX_DESKTOP.md 与 AGENTS.md，检查 Python 3.11+，运行 bootstrap.py --register-codex 完成安装、连接自检、备份并合并 MCP 配置；若已安装 Edge/Chrome，可以加 --skip-browser。不要用通用 mcpServers JSON 替代 Codex TOML。配置完成后让我重启 MCP/Codex，再调用 doctor，并实际导出一篇文章验证。微信会话只用本机的，验证码由我手动完成。

## 推荐步骤

1. 将包解压到用户可写的固定目录，安装 Python 3.11+（如果没有）。
2. Windows 已有 Edge/Chrome 时，在该目录运行：

```powershell
python bootstrap.py --skip-browser --register-codex
```

没有浏览器时运行 `python bootstrap.py --register-codex`，安装 Playwright Chromium。

3. 脚本会创建 .venv、安装固定版本依赖、执行真实 stdio 连接与 PDF 导出自检。自检失败时不会写 Codex 配置。自检成功后备份已有 config.toml，再只添加 `[mcp_servers.wechat-article-export]` 及其 env 子表；其他服务器、模型配置与注释保持不变。已存在不同配置的同名服务器时拒绝覆盖，Agent 应只核对修改该条目。
4. 重启 Codex 桌面版或 MCP 服务，在新对话中调用 wechat-article-export 的 doctor。注册后的当前对话不保证动态发现新工具。
5. 用 inspect_article 和 export_article 真实导出。遇到 AUTH_REQUIRED 则按 README 导入本机已登录微信文章地址。注册 MCP 并不代表微信认证已完成。

可显式指定配置文件：`python bootstrap.py --skip-browser --register-codex --codex-config "配置文件绝对路径"`。默认尊重 CODEX_HOME 的值，不设置或修改该环境变量。

## 手工接入

不想让安装脚本写 Codex 设置时，仅运行 `python bootstrap.py --skip-browser`。然后把生成的 codex-config.toml 内容合并到当前主机的 config.toml；或在 Codex 设置的 MCP servers 中添加 STDIO，command 指向 .venv 的 Python，args 指向 server.py。不要覆盖原有 config.toml。

本包生成 startup_timeout_sec=30、tool_timeout_sec=300，避免图像较多的文章被默认工具超时中断。安装不自动放宽 Codex 的安全/审批策略。

## 已测与未测

已在 Windows 用安装的新虚拟环境运行真实 MCP 连接、自检导出和临时 Codex 配置合并，并用本机 Codex CLI 检查配置识别。没有修改发送方的实际 Codex 配置，也没有访问目标电脑；目标电脑仍需完成上述安装、重启与实际文章验收。

依据：[OpenAI 官方 MCP 配置说明](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。Codex 桌面版、CLI 和 IDE 使用同一主机的 MCP 配置。
