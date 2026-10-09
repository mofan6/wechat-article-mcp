import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from article_export import Service
from test_export import FIXTURE, PNG
import httpx

def unpack(result):
    if result.isError:raise AssertionError(str(result.content))
    return result.structuredContent or json.loads(next(c.text for c in result.content if c.type=='text'))

async def main():
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='wechat-mcp-smoke-') as temp:
        temp=Path(temp);service=Service(temp/'state',temp/'out')
        service.request=lambda *a,**k:httpx.Response(200,content=PNG,headers={'content-type':'image/png'})
        article=service.cache_html(FIXTURE,'https://mp.weixin.qq.com/s/test')
        env=dict(os.environ,PYTHONUTF8='1',WECHAT_MCP_STATE_DIR=str(temp/'state'),WECHAT_MCP_OUTPUT_DIR=str(temp/'out'))
        params=StdioServerParameters(command=sys.executable,args=[str(root/'server.py')],env=env,cwd=str(temp))
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=120)) as client:
                await client.initialize()
                names={t.name for t in (await client.list_tools()).tools}
                assert names=={'doctor','import_wechat_session','inspect_article','get_article_stats','export_article'},names
                doctor=unpack(await client.call_tool('doctor',{}));assert doctor['pdf_ready'],doctor
                stats=unpack(await client.call_tool('get_article_stats',{'article_id':article['article_id']}));assert stats['like_count']==3 and stats['read_count']==0
                keep=[b['id'] for b in article['blocks'] if '群号' not in b['text']]
                result=unpack(await client.call_tool('export_article',{'article_id':article['article_id'],'keep_block_ids':keep,'label':'精简版'}))
                assert result['ok'],result
                assert result['validation']['selected_images']==1 and result['validation']['pdf_pages']>=1
                assert all(Path(p).is_file() for p in result['paths'].values())
                md=Path(result['paths']['markdown']).read_text(encoding='utf-8');assert '群号' not in md and 'SECRET' not in md and '招生32人' in md
                bad=unpack(await client.call_tool('inspect_article',{'url':'https://example.com/s/x'}));assert bad['code']=='INVALID_URL'
                print(json.dumps({'protocol':'initialize + list_tools + call_tool passed','tools':sorted(names),'export_validation':result['validation']},ensure_ascii=False))

if __name__=='__main__':asyncio.run(main())
