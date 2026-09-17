import unittest
from update_sources import build, extract, parse_config

class UpdateTests(unittest.TestCase):
    def test_comments_preserve_urls_and_string_content(self):
        data = parse_config('// header\n{"url":"https://x.test/a//b",/* note */"text":"comma,}","a":[1,],}')
        self.assertEqual('https://x.test/a//b', data['url'])
        self.assertEqual('comma,}', data['text'])
        self.assertEqual([1], data['a'])

    def test_only_data_interfaces(self):
        rows = extract({'sites': [{'type': 3, 'api': 'evil.jar'}, {'type': 1, 'api': 'http://x.test/api'},
                                  {'type': 1, 'api': ''}, {'type': 1, 'api': '/api', 'name': 'A', 'searchable': 0}]},
                       'https://x.test/config', {'id': 'one', 'name': 'One'})
        self.assertEqual(['https://x.test/api'], [r['url'] for r in rows])
        self.assertFalse(rows[0]['canSearch'])

    def test_empty_upstream_rejected(self):
        with self.assertRaises(ValueError):
            extract({'sites': []}, 'https://x.test/a', {'id': 'one'})

    def test_dedupe_keeps_pinned_metadata_and_tracks_moved_config(self):
        def fetch(url):
            if url == 'catalog':
                return {'resources': [{'id': 'one', 'name': 'One', 'url': 'https://new.test/config'}]}
            self.assertEqual('https://new.test/config', url)
            return {'sites': [{'type': 1, 'api': '/api'}]}
        result = build({'catalog': 'catalog', 'upstreams': ['one'], 'pinned': [
            {'id': 'saved', 'name': 'Saved', 'kind': 'json-vod', 'url': 'https://new.test/api', 'canSearch': False}]}, fetch)
        self.assertEqual(1, len(result['sources']))
        self.assertEqual('saved', result['sources'][0]['id'])
        self.assertFalse(result['sources'][0]['canSearch'])

    def test_upstream_failure_aborts_publish(self):
        def fetch(url):
            raise OSError('offline')
        with self.assertRaises(OSError):
            build({'catalog': 'catalog'}, fetch)

if __name__ == '__main__':
    unittest.main()
