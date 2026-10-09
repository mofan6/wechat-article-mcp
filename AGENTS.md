# Agent 接入说明

这是一个独立的 Python stdio MCP 服务。先读 README.md，再按以下步骤执行。

**Codex 桌面版优先读 CODEX_DESKTOP.md。** 用 bootstrap.py --register-codex 安装自检并备份合并 config.toml。Codex 不使用通用 mcpServers JSON；下面的 JSON 路径适用于其他 MCP 宿主。

1. 将包解压到固定目录，检查 Python >= 3.11。运行 `python bootstrap.py`；已有 Edge/Chrome 时可运行 `python bootstrap.py --skip-browser`。安装依赖与浏览器下载需要网络。Linux Chromium 可能还需系统依赖，参见 README。
2. 将生成的 `mcp-config.json` 合并到当前 Agent 的 MCP 配置。不要直接覆盖原有配置。不同宿主字段可能不同；本服务固定使用 command + args 的 stdio 接口。主机需要允许安装/注册 MCP；压缩包无法自动获得此权限。
3. 重启/重新加载 MCP 宿主，调用 `doctor`，确认 PDF 浏览器可用。
4. 调用 `inspect_article(url)`。若 AUTH_REQUIRED，让用户在本机已登录微信打开文章并手动完成验证。用宿主已有的、获授权的浏览器或电脑操作能力读取完整文章 URL，写入 UTF-8 本地文件；再调用 `import_wechat_session(local_file)`。不能自动绕过验证、读取微信数据库或导入发送方的登录凭据。
5. 正常导出：将 inspect 返回的 article_id 传给 export_article，formats=["markdown","pdf"]。
6. 精简去广告：先阅读 blocks，并通过宿主的本地图片查看工具查看 images.local_path。广告候选只是提示。按照用户要求明确选择保留的块 ID；保留数据表、成绩图、招生目录、参考书与备考建议，排除二维码、联系方式、商品、喜报、课程推广、推荐阅读和无关装饰。调用 export_article(keep_block_ids=[...],label="精简版")。不会凭图片序号套用上一所学校的规则。
7. 将返回文件与 images 文件夹作为整体交付；检查 Markdown 相对图片路径，PDF 用本机可用的渲染/查看工具复核。服务的 validation 检查页数与图像载入，不代表语义或每页视觉质量均已人工审查。

同一段正文内混有广告时，用 export_article 的 text_overrides 按块 ID 提供去掉推销后的纯文本，保持事实、数字和有效建议。两个输出使用同一份筛选与改写结果，原始缓存不变。

标准输出只用于 MCP 协议，不要往 server.py 加 print。登录态在 .state/session.json，只存本机；不得将 .state、exports、.venv 或会话文件重新打包发送。凭据文件不应上传到聊天记录。MCP 工具描述和本文本都不替代用户授权。

未包含 Excel 合集批量导出、微信账号登录、抓包代理或证书安装。核心能力是单篇文章 Markdown/PDF 导出、按正文块去广告和文章三项统计提取。
