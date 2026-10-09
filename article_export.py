from __future__ import annotations
import base64
import hashlib
import html
import json
import os
import re
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
import httpx
from version import __version__,DESIGNED_BY
from bs4 import BeautifulSoup, Tag
from markdownify import markdownify

ROOT = Path(__file__).resolve().parent
AUTH_KEYS = {'key', 'uin', 'pass_ticket', 'devicetype', 'version', 'lang', 'ascene', 'wx_header'}
SECRET_KEYS = {'key','uin','pass_ticket','exportkey','sessionid','session_id','auth','token','access_token'}
AD_PATTERN = re.compile(r'二维码|群号|交流群|火爆销售|淘宝|购买资料|指导套餐|小班课|答疑服务|推荐阅读|扫码|1V1|一对一|正版图书|课程套餐')
IMAGE_HOSTS = {'mmbiz.qpic.cn','mmbiz.qlogo.cn','wx.qlogo.cn','res.wx.qq.com','mp.weixin.qq.com'}

class ExportError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)

def public_url(url: str) -> str:
    p = urlsplit(url)
    # Nested credential-bearing redirects should never appear in deliverables.
    if re.search(r'(?:%26|&)(?:key|uin|pass_ticket|exportkey)(?:%3[dD]|=)',url):
        query = {k:v for k,v in parse_qs(p.query).items() if k in {'__biz','mid','idx','sn'}}
    else:
        query = {k:v for k,v in parse_qs(p.query).items() if k.lower() not in SECRET_KEYS}
    return urlunsplit((p.scheme,p.netloc,p.path,urlencode(query,doseq=True),p.fragment))

def article_url(url):
    if not isinstance(url,str):raise ExportError('INVALID_URL','Article URL must be a string.')
    try:
        p=urlsplit(url.strip());port=p.port
    except ValueError:raise ExportError('INVALID_URL','Malformed article URL.') from None
    if p.scheme not in {'https','http'} or p.hostname!='mp.weixin.qq.com' or not (p.path=='/s' or p.path.startswith('/s/')) or p.username or p.password or port not in (None,443,80):
        raise ExportError('INVALID_URL','Only mp.weixin.qq.com/s article URLs are accepted.')
    return public_url(url.strip())

def safe_stem(title):
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',title).strip(' .')[:90] or 'WeChatArticle'
    if name.upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:name='article_'+name
    return name

def browser_executable():
    custom=os.environ.get('WECHAT_MCP_BROWSER')
    if custom and Path(custom).is_file():return custom
    candidates=[]
    if sys.platform=='win32':
        for env in ('PROGRAMFILES(X86)','PROGRAMFILES','LOCALAPPDATA'):
            base=os.environ.get(env,'')
            if base:candidates += [str(Path(base)/'Microsoft/Edge/Application/msedge.exe'),str(Path(base)/'Google/Chrome/Application/chrome.exe')]
    elif sys.platform=='darwin':
        candidates=['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge']
    else:
        candidates=[shutil.which('chromium') or '',shutil.which('google-chrome') or '',shutil.which('chromium-browser') or '']
    return next((p for p in candidates if p and Path(p).is_file()),None)

class Service:
    def __init__(self, state_dir=None, output_dir=None):
        self.state=Path(state_dir or os.environ.get('WECHAT_MCP_STATE_DIR',ROOT/'.state')).resolve()
        self.output=Path(output_dir or os.environ.get('WECHAT_MCP_OUTPUT_DIR',ROOT/'exports')).resolve()
        self.state.mkdir(parents=True,exist_ok=True)

    def doctor(self):
        from playwright.sync_api import sync_playwright
        browser=browser_executable()
        with sync_playwright() as p:
            bundled=p.chromium.executable_path
        return {'version':__version__,'designed_by':DESIGNED_BY,'python':sys.version.split()[0], 'platform':sys.platform,
                'pdf_ready': bool(browser or Path(bundled).is_file()),
                'browser':browser or (bundled if Path(bundled).is_file() else None),
                'output_dir':str(self.output),'session_configured':(self.state/'session.json').exists(),
                'setup_action':None if browser or Path(bundled).is_file() else 'Run .venv Python -m playwright install chromium',
                'session_note':'A saved session may expire; only an article fetch validates it.'}

    def import_session(self,local_file):
        path=Path(local_file).expanduser().resolve()
        if not path.is_file() or path.stat().st_size>1024*1024:return {'ok':False,'code':'INVALID_SESSION_FILE','message':'Use an existing UTF-8 URL file, at most 1 MB.'}
        try:
            raw=path.read_text(encoding='utf-8-sig').strip()
            if raw.startswith('{'):raw=json.loads(raw)['url']
            article_url(raw)
            auth={k:v[0] for k,v in parse_qs(urlsplit(raw).query).items() if k in AUTH_KEYS}
            if not {'key','uin'}<=auth.keys():raise ValueError()
        except (ValueError,KeyError,ExportError):return {'ok':False,'code':'INVALID_SESSION_FILE','message':'No authenticated WeChat article URL found. Use this machine’s logged-in WeChat browser URL including key and uin.'}
        dest=self.state/'session.json'
        dest.write_text(json.dumps(auth),encoding='utf-8')
        if os.name!='nt':dest.chmod(0o600)
        return {'ok':True,'message':'Session imported locally. It may expire; no credentials returned.'}

    def request(self,url,hosts,params=None):
        # Redirects are checked before each request; credentials are sent only to mp.weixin.qq.com.
        with httpx.Client(timeout=40,follow_redirects=False,headers={'User-Agent':'Mozilla/5.0'}) as client:
            for _ in range(6):
                p=urlsplit(url)
                if p.scheme not in ('http','https') or p.hostname not in hosts or p.username or p.password or p.port not in (None,80,443):raise ExportError('UNSUPPORTED_HOST','Article/image host is outside the supported WeChat domains.')
                try:
                    response=client.get(url,params=params)
                except httpx.HTTPError:
                    raise ExportError('NETWORK_ERROR','WeChat request failed. Check network and proxy, then retry.') from None
                params=None
                if response.status_code in (301,302,303,307,308):
                    url=urljoin(str(response.url),response.headers.get('location',''));continue
                if response.status_code==429:raise ExportError('RATE_LIMITED','WeChat rate limited this request. Wait before retrying.')
                if response.status_code>=400:raise ExportError('HTTP_ERROR',f'WeChat returned HTTP {response.status_code}.')
                if len(response.content)>40*1024*1024:raise ExportError('TOO_LARGE','An article or image exceeds the 40 MB limit.')
                return response
        raise ExportError('REDIRECT_ERROR','Too many redirects.')

    def inspect(self,url):
        try:
            clean_url=article_url(url)
            auth=json.loads((self.state/'session.json').read_text()) if (self.state/'session.json').exists() else {}
            response=self.request(clean_url,{'mp.weixin.qq.com'},auth)
            return self.cache_html(response.content.decode('utf-8',errors='replace'),clean_url)
        except ExportError as e:return {'ok':False,'code':e.code,'message':e.message}

    def cache_html(self,raw,url):
        soup=BeautifulSoup(raw,'html.parser');title=soup.select_one('#activity-name');content=soup.select_one('#js_content')
        if not title or not content:
            if '操作过于频繁' in raw:raise ExportError('RATE_LIMITED','WeChat requests are too frequent. Wait before retrying.')
            if '已被发布者删除' in raw or '内容已被删除' in raw:raise ExportError('ARTICLE_REMOVED','This article has been removed.')
            raise ExportError('AUTH_REQUIRED','Open this article in your logged-in WeChat browser, finish any verification manually, save its authenticated URL to a local file and call import_wechat_session. Alternatively use a publicly accessible article.')
        article_id=uuid.uuid4().hex
        cache=self.state/article_id;cache.mkdir();(cache/'images').mkdir()
        # Cache raw source locally for metrics; it is never included in the ZIP or returned.
        (cache/'source.html').write_text(raw,encoding='utf-8')
        for node in content.select('script,style,iframe,video,audio'):node.decompose()
        for a in content.select('a'):
            if a.get('href','').startswith(('http:','https:')):a['href']=public_url(a['href'])
            else:a.attrs.pop('href',None)
        blocks=[];images=[];warnings=[]
        def emit(kind,text='',markup='',image=None):
            block={'id':f'b{len(blocks)+1:04d}','kind':kind,'text':text,'html':markup,'ad_review_candidate':bool(AD_PATTERN.search(text))}
            if image:block['image_id']=image
            blocks.append(block)
        def visit(node):
            if not isinstance(node,Tag):
                if str(node).strip():emit('text',str(node).strip(),'<p>'+html.escape(str(node).strip())+'</p>')
                return
            if node.name=='img':
                src=node.get('data-src') or node.get('src')
                if not src:return
                imgid=f'i{len(images)+1:03d}'
                record={'id':imgid,'source_url':public_url(urljoin(url,src)),'local_path':None,'downloaded':False,'alt':node.get('alt','')}
                try:
                    r=self.request(urljoin(url,src),IMAGE_HOSTS)
                    mime=r.headers.get('content-type','').split(';')[0]
                    ext={'image/jpeg':'jpg','image/png':'png','image/gif':'gif','image/webp':'webp'}.get(mime)
                    if not ext:raise ExportError('IMAGE_FORMAT','Image format is not supported.')
                    path=cache/'images'/f'{imgid}.{ext}';path.write_bytes(r.content)
                    record.update(local_path=str(path),downloaded=True,mime=mime)
                except ExportError as e:record['error_code']=e.code;warnings.append(f'{imgid}: {e.code}')
                images.append(record);emit('image',record['alt'],image=imgid);return
            if node.name=='table':
                for tag in node.find_all(True):tag.attrs={k:v for k,v in tag.attrs.items() if k in ('rowspan','colspan','href')}
                node.attrs={};emit('table',node.get_text(' ',strip=True),str(node));return
            if node.find(['p','div','section','table','img','h1','h2','h3','h4','ul','ol']):
                for child in list(node.children):visit(child)
            else:
                text=node.get_text('',strip=False).strip()
                if not text:return
                for tag in [node,*node.find_all(True)]:
                    tag.attrs={k:v for k,v in tag.attrs.items() if k in ('href',)}
                    if tag.name not in {'a','strong','b','em','i','br','h1','h2','h3','h4','p','li'}:tag.name='span'
                markup=str(node)
                if node.name not in {'p','h1','h2','h3','h4','li'}:markup='<p>'+markup+'</p>'
                emit('text',text,markup)
        for child in list(content.children):visit(child)
        for i,b in enumerate(blocks):
            if b['kind']=='image':b['ad_review_candidate']=any(x['ad_review_candidate'] for x in blocks[max(0,i-2):i]+blocks[i+1:i+3] if x['kind']=='text')
        author=soup.select_one('#js_name')
        data={'article_id':article_id,'title':title.get_text(strip=True),'author':author.get_text(strip=True) if author else '', 'url':public_url(url),'fetched_at':datetime.now(timezone.utc).isoformat(),'blocks':blocks,'images':images,'warnings':warnings}
        (cache/'article.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        return {'ok':True,**{k:v for k,v in data.items() if k!='blocks'},'blocks':[{k:v for k,v in b.items() if k!='html'} for b in blocks], 'review_note':'Candidates are hints, not automatic deletion. Review image files; chart watermarks alone are not a reason to discard data.'}

    def load(self,article_id):
        if not re.fullmatch('[a-f0-9]{32}',article_id):raise ExportError('INVALID_ARTICLE_ID','Use article_id returned by inspect_article.')
        cache=self.state/article_id
        if not (cache/'article.json').is_file():raise ExportError('CACHE_NOT_FOUND','Call inspect_article on this computer first.')
        return cache,json.loads((cache/'article.json').read_text(encoding='utf-8'))

    def stats(self,article_id):
        try:
            cache,data=self.load(article_id);raw=(cache/'source.html').read_text(encoding='utf-8')
            patterns={'read_count':[r"var\s+read_num_new\s*=\s*'(\d+)'",r"var\s+read_num\s*=\s*'(\d+)'"],'share_count':[r"\bshare_count\s*:\s*'(\d+)'"],'like_count':[r"\bold_like_count\s*:\s*'(\d+)'"]}
            result={}
            for name,regexes in patterns.items():
                match=next((m for pattern in regexes if (m:=re.search(pattern,raw))),None)
                result[name]=int(match[1]) if match else None
            return {'ok':True,'title':data['title'],'fetched_at':data['fetched_at'],**result,'like_definition':'thumbs-up old_like_count; excludes heart/in-looking like_count','missing_metrics':[k for k,v in result.items() if v is None]}
        except ExportError as e:return {'ok':False,'code':e.code,'message':e.message}

    def export(self,article_id,formats=None,keep_block_ids=None,exclude_block_ids=None,label='',text_overrides=None):
        try:
            cache,data=self.load(article_id);formats=formats if formats is not None else ['markdown','pdf']
            if not formats or set(formats)-{'markdown','pdf'}:raise ExportError('INVALID_FORMAT','Choose markdown and/or pdf.')
            known={b['id'] for b in data['blocks']}
            supplied=set(keep_block_ids or [])|set(exclude_block_ids or [])|set(text_overrides or {})
            if supplied-known:raise ExportError('INVALID_BLOCK_ID','Unknown block IDs: '+','.join(sorted(supplied-known)))
            for b in data['blocks']:
                if b['id'] in (text_overrides or {}) and (b['kind']!='text' or not isinstance(text_overrides[b['id']],str) or not text_overrides[b['id']].strip()):raise ExportError('INVALID_TEXT_OVERRIDE','Text overrides must be nonempty plain text for text blocks only.')
            blocks=[dict(b) for b in data['blocks'] if (keep_block_ids is None or b['id'] in keep_block_ids) and b['id'] not in (exclude_block_ids or [])]
            for b in blocks:
                if b['id'] in (text_overrides or {}):
                    b['text']=text_overrides[b['id']];b['html']='<p>'+html.escape(b['text']).replace('\n','<br>')+'</p>'
            if not blocks:raise ExportError('EMPTY_EXPORT','No content remains after filtering.')
            images={i['id']:i for i in data['images']};selected=[images[b['image_id']] for b in blocks if b['kind']=='image']
            if any(not i['downloaded'] for i in selected):raise ExportError('MISSING_IMAGES','Selected images did not download. Retry inspection or explicitly exclude those image blocks.')
            dirname=safe_stem(data['title'])+'_'+uuid.uuid4().hex[:8];target=self.output/dirname;target.mkdir(parents=True)
            stem=safe_stem(data['title']+(('（'+label+'）') if label else ''));assets=target/'images';assets.mkdir()
            mdparts=[];htmlparts=[]
            for block in blocks:
                if block['kind']=='image':
                    im=images[block['image_id']];src=Path(im['local_path']);shutil.copy2(src,assets/src.name)
                    mdparts.append(f'![文章图片](images/{src.name})')
                    uri='data:'+im['mime']+';base64,'+base64.b64encode(src.read_bytes()).decode()
                    htmlparts.append('<figure><img src="'+uri+'"></figure>')
                else:
                    mdparts.append(markdownify(block['html'],heading_style='ATX').strip());htmlparts.append(block['html'])
            markdown=f"# {data['title']}\n\n{data['author']}\n\n原文：{data['url']}\n\n"+'\n\n'.join(mdparts)+'\n'
            markdown=re.sub(r'\n{3,}','\n\n',markdown)
            paths={}
            if 'markdown' in formats:
                path=target/(stem+'.md');path.write_text(markdown,encoding='utf-8');paths['markdown']=str(path)
            pages=None
            if 'pdf' in formats:
                from playwright.sync_api import sync_playwright
                from pypdf import PdfReader
                css='''@page{size:A4;margin:15mm 16mm 17mm}body{font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif;font-size:11pt;line-height:1.7;color:#222;margin:0}h1{font-size:20pt;line-height:1.4}h2,h3,h4{break-after:avoid}p{orphans:3;widows:3}figure{margin:12pt 0;break-inside:avoid}img{max-width:100%;max-height:220mm;height:auto;object-fit:contain;display:block;margin:auto}table{border-collapse:collapse;width:100%;font-size:10pt}th,td{border:1px solid #bbb;padding:5pt}a{color:#155e86;overflow-wrap:anywhere}'''
                document='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>'+css+'</style><body><h1>'+html.escape(data['title'])+'</h1><p>'+html.escape(data['author'])+' · <a href="'+html.escape(data['url'],quote=True)+'">原文链接</a></p>'+''.join(htmlparts)+'</body></html>'
                path=target/(stem+'.pdf')
                try:
                    with sync_playwright() as p:
                        kwargs={'headless':True};exe=browser_executable()
                        if exe:kwargs['executable_path']=exe
                        browser=p.chromium.launch(**kwargs)
                        try:
                            page=browser.new_page();page.route('**/*',lambda route:route.abort())
                            page.set_content(document,wait_until='load',timeout=60000)
                            page.evaluate('document.fonts.ready')
                            count=page.evaluate('() => [...document.images].filter(i => i.complete && i.naturalWidth > 0).length')
                            if count!=len(selected):raise ExportError('PDF_IMAGE_ERROR','Some selected images did not render in PDF.')
                            page.pdf(path=str(path),format='A4',print_background=True,prefer_css_page_size=True,display_header_footer=True,header_template='<span></span>',footer_template='<div style="font-size:9px;text-align:center;width:100%;color:#777"><span class="pageNumber"></span> / <span class="totalPages"></span></div>')
                        finally:browser.close()
                except ExportError:raise
                except Exception:
                    raise ExportError('PDF_BROWSER_ERROR','PDF browser failed. Call doctor; install Chromium with .venv Python -m playwright install chromium, or set WECHAT_MCP_BROWSER to an installed browser executable.') from None
                pages=len(PdfReader(path).pages);paths['pdf']=str(path)
            validation={'selected_blocks':len(blocks),'excluded_blocks':len(data['blocks'])-len(blocks),'selected_images':len(selected),'pdf_pages':pages,'relative_image_links_valid':all((assets/Path(i['local_path']).name).is_file() for i in selected)}
            (target/'export-info.json').write_text(json.dumps({'title':data['title'],'source':data['url'],'fetched_at':data['fetched_at'],'retained_block_ids':[b['id'] for b in blocks],'rewritten_block_ids':list(text_overrides or {}),'validation':validation},ensure_ascii=False,indent=2),encoding='utf-8')
            return {'ok':True,'title':data['title'],'paths':paths,'images_dir':str(assets),'validation':validation}
        except ExportError as e:
            result={'ok':False,'code':e.code,'message':e.message}
            if 'paths' in locals() and paths:result['partial_outputs']=paths
            return result
