"""Portable stdio MCP. stdout is reserved for protocol messages."""
from mcp.server.fastmcp import FastMCP
from article_export import Service
import asyncio

service = Service()
mcp = FastMCP('wechat-article-export', instructions='Export WeChat articles to local Markdown/PDF. Start with doctor. On AUTH_REQUIRED ask the user to open the article in their logged-in WeChat browser and import its authenticated URL using a local file. For ad removal inspect_article first, review its blocks/images, then export with explicit keep_block_ids. Never invent missing metrics or solve verification automatically.')

@mcp.tool()
async def doctor() -> dict:
    """Check runtime, PDF browser and local session status; return setup actions."""
    return await asyncio.to_thread(service.doctor)

@mcp.tool()
def import_wechat_session(local_file: str) -> dict:
    """Import this computer's WeChat browser authenticated article URL from a UTF-8 local file (plain URL or JSON {url: ...}). Do not put credentials directly in tool arguments. No browser/login automation. Returns only whether session parameters were found."""
    return service.import_session(local_file)

@mcp.tool()
async def inspect_article(url: str) -> dict:
    """Fetch article and images, cache locally, return article_id plus numbered text/image blocks and review candidates. Downloaded image paths let the Agent inspect data charts versus advertisements. Credentials are omitted. Verification/rate limits return actionable error codes."""
    return await asyncio.to_thread(service.inspect,url)

@mcp.tool()
def get_article_stats(article_id: str) -> dict:
    """Read exact cached read_count, share_count and thumbs-up old_like_count. Missing values are null, never zero. Counts reflect fetch time, not publication time."""
    return service.stats(article_id)

@mcp.tool()
async def export_article(article_id: str, formats: list[str] | None = None,
                   keep_block_ids: list[str] | None = None,
                   exclude_block_ids: list[str] | None = None,
                   label: str = '', text_overrides: dict[str, str] | None = None) -> dict:
    """Export cached article as markdown/pdf (both by default). All blocks retained unless explicit keep/exclude IDs are supplied after inspection. For clean edition remove ads, QR images and course promos while preserving data figures and substantive paragraphs. text_overrides maps text block IDs to revised plain text when ads are mixed into useful prose; preserve source facts and numbers. Output is a unique local directory, PDF and MD share the same reviewed content; images use relative links. Returns absolute paths and validation results. label is an optional filename suffix, e.g. 精简版."""
    return await asyncio.to_thread(service.export,article_id, formats, keep_block_ids, exclude_block_ids, label, text_overrides)

if __name__ == '__main__':
    mcp.run(transport='stdio')
