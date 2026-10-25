import unittest
from tvbox_catalog import canonical, discover, validate_vod, source_key


class CatalogTests(unittest.TestCase):
    def test_proxy_and_unicode(self):
        self.assertEqual(canonical('https://gh-proxy.com/https://raw.githubusercontent.com/a/b/main/x'), 'https://raw.githubusercontent.com/a/b/main/x')
        self.assertTrue(canonical('http://肥猫.net/tv').startswith('https://xn--'))
        with self.assertRaises(ValueError):
            canonical('https://user:password@example.com/config')

    def test_nested_cycles_failure_and_plugin_config(self):
        fixtures = {
            'https://example.com/root': {'storeHouse':[{'sourceUrl':'./list','sourceName':'list'}]},
            'https://example.com/list': {'urls':[{'url':'./root'}, {'url':'./config'}, {'url':'./broken'}]},
            'https://example.com/config': {'sites':[{'type':3,'api':'csp_Test'}], 'lives':[]},
        }
        configs, report = discover([{'url':'https://example.com/root','name':'root'}], fixtures.__getitem__)
        self.assertEqual(len(configs), 1)
        self.assertEqual(report['visited'], 4)
        self.assertEqual(len(report['errors']), 1)

    def test_vod_requires_catalog_data(self):
        rows = [dict(url='https://example.com/api?token=abc')]
        def valid(url):
            self.assertIn('token=abc', url)
            self.assertIn('ac=detail', url)
            return {'list':[{'vod_id':1,'vod_name':'test'}]}
        self.assertEqual(validate_vod(rows, valid), (rows, []))
        good, errors = validate_vod(rows, lambda _: {'message':'login required'})
        self.assertEqual(good, [])
        self.assertEqual(len(errors), 1)

    def test_equivalent_api_deduplication_keeps_tokens(self):
        self.assertEqual(source_key('https://x.test/api/?ac=list'), source_key('https://x.test/api'))
        self.assertNotEqual(source_key('https://x.test/api?token=one'), source_key('https://x.test/api?token=two'))

    def test_limit(self):
        configs, report = discover([{'url':'https://example.com/root','name':'root'}], lambda _: {'urls':[{'url':'./child'}]}, limit=1)
        self.assertEqual(report['errors'][0]['remaining'], 1)


if __name__ == '__main__':
    unittest.main()
