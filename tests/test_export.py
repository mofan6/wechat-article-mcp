import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from article_export import Service, ExportError, public_url, article_url

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
FIXTURE='''<h1 id="activity-name">测试大学招生数据</h1><b id="js_name">测试公众号</b><div id="js_content"><p>扫码购买资料，群号123</p><h2>招生数据</h2><p>招生32人，复试线330分。</p><img data-src="https://mmbiz.qpic.cn/test.png"><section><span><table><tr><th>学校</th><th>人数</th></tr><tr><td>测试大学</td><td>32</td></tr></table></span></section><p><a href="https://mp.weixin.qq.com/s/x?key=SECRET&amp;uin=PRIVATE&amp;mid=123">详情</a></p></div><script>var read_num_new = '0';var x={share_count:'12',old_like_count:'3',like_count:'7'};</script>'''

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.service=Service(self.root/'state',self.root/'out')
        self.service.request=lambda *a,**k:httpx.Response(200,content=PNG,headers={'content-type':'image/png'})
    def tearDown(self):self.tmp.cleanup()
    def inspect_fixture(self):return self.service.cache_html(FIXTURE,'https://mp.weixin.qq.com/s/test?key=SECRET')
    def test_article_hosts(self):
        for u in ['https://evil.example/s/x','file:///tmp/x','https://mp.weixin.qq.com.evil.example/s/x','https://mp.weixin.qq.com:bad/s/x']:
            with self.assertRaises(ExportError):article_url(u)
    def test_session_not_returned(self):
        source=self.root/'session.txt';source.write_text('https://mp.weixin.qq.com/s/x?key=SECRET&uin=PRIVATE&pass_ticket=TICKET',encoding='utf-8')
        result=self.service.import_session(str(source));self.assertTrue(result['ok']);self.assertNotIn('SECRET',json.dumps(result))
    def test_full_md_table_and_secrets(self):
        article=self.inspect_fixture();result=self.service.export(article['article_id'],['markdown'])
        md=Path(result['paths']['markdown']).read_text(encoding='utf-8')
        self.assertNotIn('SECRET',md);self.assertNotIn('PRIVATE',md);self.assertIn('| 学校 | 人数 |',md)
        self.assertTrue(result['validation']['relative_image_links_valid'])
        self.assertEqual(result['validation']['selected_images'],1)
    def test_clean_filter_and_source_order(self):
        article=self.inspect_fixture();keep=[b['id'] for b in article['blocks'] if not b['ad_review_candidate'] or b['kind']=='image']
        result=self.service.export(article['article_id'],['markdown'],list(reversed(keep)),label='精简版')
        self.assertTrue(result['ok']);md=Path(result['paths']['markdown']).read_text(encoding='utf-8')
        self.assertNotIn('群号123',md);self.assertIn('招生32人',md);self.assertIn('images/',md)
        self.assertLess(md.index('招生32人'),md.index('images/'))
    def test_missing_not_zero_and_thumb_definition(self):
        article=self.inspect_fixture();stats=self.service.stats(article['article_id'])
        self.assertEqual(stats['read_count'],0);self.assertEqual(stats['like_count'],3)
        other=self.service.cache_html(FIXTURE.split('<script>')[0],'https://mp.weixin.qq.com/s/other')
        self.assertIsNone(self.service.stats(other['article_id'])['read_count'])
    def test_verification(self):
        with self.assertRaises(ExportError) as ctx:self.service.cache_html('环境异常，完成验证后即可继续访问。','https://mp.weixin.qq.com/s/x')
        self.assertEqual(ctx.exception.code,'AUTH_REQUIRED')
    def test_bad_selection_and_no_overwrite(self):
        article=self.inspect_fixture();aid=article['article_id']
        self.assertEqual(self.service.export(aid,['markdown'],[])['code'],'EMPTY_EXPORT')
        self.assertEqual(self.service.export(aid,['markdown'],['x'])['code'],'INVALID_BLOCK_ID')
        first=self.service.export(aid,['markdown']);second=self.service.export(aid,['markdown'])
        self.assertNotEqual(first['paths']['markdown'],second['paths']['markdown'])
    def test_image_failure_explicit(self):
        def fail(*a,**k):raise ExportError('NETWORK_ERROR','test')
        self.service.request=fail;article=self.inspect_fixture()
        self.assertTrue(article['warnings']);result=self.service.export(article['article_id'],['markdown'])
        self.assertEqual(result['code'],'MISSING_IMAGES')
    def test_overrides_keep_source_unchanged(self):
        article=self.inspect_fixture();b=next(b for b in article['blocks'] if b['text']=='招生32人，复试线330分。')
        result=self.service.export(article['article_id'],['markdown'],text_overrides={b['id']:'招生32人。'})
        self.assertTrue(result['ok']);self.assertIn('招生32人。',Path(result['paths']['markdown']).read_text(encoding='utf-8'))
        _,source=self.service.load(article['article_id']);self.assertEqual(next(x for x in source['blocks'] if x['id']==b['id'])['text'],'招生32人，复试线330分。')
    def test_redirect_host_checked_before_second_request(self):
        # Validation of the same host boundary used on every redirect hop.
        with self.assertRaises(ExportError):Service.request(self.service,'https://127.0.0.1/s',{'mp.weixin.qq.com'})

if __name__=='__main__':unittest.main()
