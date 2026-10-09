# 验证记录

日期：2026-10-09。本地：Windows，Python 3.12，已安装 Microsoft Edge。GitHub Actions：Windows 与 Ubuntu，Python 3.12。

## 已通过

- 独立虚拟环境安装 requirements.txt 中的全部依赖。
- 10 项单元测试：文章域名限制、会话导入不返回凭据、Markdown 表格与链接脱敏、保留块筛选与原始顺序、真实零与缺失指标的区别、拇指点赞定义、微信验证错误、错误块 ID/空筛选、导出不覆盖、图片失败显式报告、文字覆盖不修改原始缓存。
- 使用真实 MCP 客户端和 stdio 子进程完成 initialize、list_tools、call_tool。发现 5 个工具，完成 doctor、统计读取、精简版 Markdown/PDF 导出及错误 URL 检查；测试不依赖微信或外网。
- 用之前已取得的南航文章与本地图像进行回归：40 张原图与所有有意义的正文 p 文本均保留；明确选择 20 张数据图表后成功导出两个格式；验证相对图片路径，并读取该文章三项统计字段。精简回归 PDF 23 页，检查首页、中间图表页和末页渲染。
- 压缩包解压到另一个目录，使用绝对路径从不同工作目录启动服务，MCP smoke 测试通过。
- 在新解压目录实际运行 bootstrap.py --skip-browser，成功创建新的 .venv、安装依赖并生成绝对路径 mcp-config.json。使用这套新解释器再次完成 MCP smoke 测试。
- ZIP 完整性与文件清单检查：不含 .state、会话、历史文章、.venv、exports 或本项目电脑私有绝对路径。

## 验证边界

追加 Codex 桌面版适配：提供 CODEX_DESKTOP.md 和 TOML 配置生成/注册脚本。另有 3 项配置测试，验证备份、保留其他服务器/模型与注释、重复注册、同名冲突不覆盖、含中文和空格的路径。配置识别使用本机 Codex CLI 的临时命令行覆盖，不写发送方实际 Codex 设置。

GitHub Actions 的 Windows 与 Ubuntu 两个平台均已通过依赖安装、13 项单元测试、真实 stdio/PDF 导出自检和发行包构建：[测试记录](https://github.com/mofan6/wechat-article-mcp/actions/runs/37905041185)。Ubuntu 安装了 Playwright Chromium 系统依赖与 Noto CJK 字体。

本次没有在 macOS 上运行测试；代码和安装入口提供相应路径及 Chromium 支持。目标机器的网络、权限和中文字体仍需按 doctor 和安装自检确认。

实际微信文章访问受登录态、网络、微信验证及频率限制影响。回归使用本机已取得的原文缓存，没有将登录会话复制到包中，也不表示每个公众号链接都能无登录读取。

服务验证 PDF 图像载入、文件生成和页数；针对新的文章，Agent 仍应检查关键页面的视觉效果。正文块广告候选是提示，精简应依据 Agent 审查结果明确筛选，不能保证自动识别所有广告。
