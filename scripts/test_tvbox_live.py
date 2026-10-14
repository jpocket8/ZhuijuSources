import unittest
from tvbox_live import extract, from_text, safe_url

class LiveImportTest(unittest.TestCase):
    def test_inline_groups_multiple_routes_and_deduplication(self):
        config={'spider':'evil.jar','lives':[{'name':'电视','groups':[{'group':'新闻','channels':[{'name':'ABC','urls':['https://a.test/live','https://b.test/live','https://a.test/live','file:///etc/passwd'],'logo':'https://a.test/logo.png'}]}]}]}
        rows, files, skipped=extract(config,'https://a.test/config.json',{'id':'a','name':'来源'},lambda _:self.fail())
        self.assertEqual(len(rows),1);self.assertEqual(skipped,0)
        text=next(iter(files.values()));self.assertEqual(text.count('#EXTINF'),2)
        self.assertIn('group-title="新闻"',text);self.assertNotIn('file:',text)
        self.assertEqual(extract(config,'https://a.test/config.json',{'id':'a','name':'来源'})[0][0]['id'],rows[0]['id'])
    def test_text_and_m3u(self):
        text=from_text('新闻,#genre#\nABC,https://a.test/a#https://b.test/b\nABC,https://a.test/a','https://a.test/list.txt')
        self.assertEqual(text.count('#EXTINF'),2)
        m3u='#EXTM3U\n#EXTINF:-1 tvg-id="abc" tvg-country="AU" group-title="News, AU",ABC\n#EXTVLCOPT:http-user-agent=TV\n/stream.m3u8\n'
        output=from_text(m3u,'https://a.test/list.m3u')
        self.assertIn('https://a.test/stream.m3u8',output);self.assertIn('tvg-id="abc"',output);self.assertIn('tvg-country="AU"',output)
        self.assertIn('group-title="News, AU"',output);self.assertIn('http-user-agent=TV',output)
    def test_remote_subscription_failure_is_not_published_as_empty(self):
        config={'lives':[{'name':'TV','url':'list.txt'}]}
        rows,files,_=extract(config,'https://a.test/config.json',{'id':'a','name':'A'},lambda _: 'ABC,https://a.test/live')
        self.assertEqual(len(rows),1)
        with self.assertRaises(ValueError):extract(config,'https://a.test/config.json',{'id':'a','name':'A'},lambda _:'<html>error</html>')
    def test_plugins_and_non_https_subscriptions_are_skipped(self):
        rows,files,skipped=extract({'lives':[{'url':'proxy://do=live'},{'url':'http://a.test/list'}]},'https://a.test/config',{'id':'a','name':'A'})
        self.assertEqual((rows,files,skipped),([],{},2));self.assertIsNone(safe_url('https://user:pass@a.test/'))
    def test_bad_upstream_retains_last_good_playlist_and_other_sources(self):
        config={'lives':[{'name':'TV','url':'list.txt'}]};upstream={'id':'a','name':'A'}
        rows,files,_=extract(config,'https://a.test/config',upstream,lambda _:'ABC,https://a.test/live')
        errors=[]
        kept,content,_=extract(config,'https://a.test/config',upstream,lambda _:'bad response',files,errors)
        self.assertEqual(kept,rows);self.assertEqual(content,files);self.assertTrue(errors[0]['retained'])
        empty,_,_=extract(config,'https://a.test/config',upstream,lambda _:'bad response',{},[])
        self.assertEqual(empty,[])
