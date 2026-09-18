import unittest,json
from update_youtube import parse,duration
class YouTubeTests(unittest.TestCase):
    channel={'channelId':'UC7Vl0YiY0rDlovqcCFN4yTA','name':'央视电视剧','category':'剧集'}
    def html(self,title='《测试剧》EP01',seconds='40:00',identity=None):
        data={'metadata':{'channelMetadataRenderer':{'externalId':identity or self.channel['channelId']}},'contents':{'lockupViewModel':{
            'contentType':'LOCKUP_CONTENT_TYPE_VIDEO','contentId':'abcdefghijk','metadata':{'lockupMetadataViewModel':{'title':{'content':title}}},
            'contentImage':{'thumbnailBadgeViewModel':{'text':seconds}}}}}
        return 'var ytInitialData = '+json.dumps(data)+';'
    def test_group_title_and_episode(self):
        row=parse(self.html(),self.channel)[0]
        self.assertEqual('测试剧',row['programme']);self.assertEqual('第01集',row['episode'])
    def test_unknown_title_not_guessed(self):
        self.assertEqual('完整官方标题',parse(self.html('完整官方标题'),self.channel)[0]['programme'])
    def test_wrong_channel_rejected(self):
        with self.assertRaises(ValueError):parse(self.html(identity='wrong'),self.channel)
    def test_short_or_trailer_cannot_replace_catalog(self):
        for html in [self.html(seconds='01:30'),self.html(title='电影预告')]:
            with self.assertRaises(ValueError):parse(html,self.channel)
    def test_duration(self):
        self.assertEqual(3723,duration('1:02:03'));self.assertEqual(0,duration('LIVE'))
