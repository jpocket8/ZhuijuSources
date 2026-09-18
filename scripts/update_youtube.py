"""Index public official-channel video metadata; playback stays in YouTube's embedded player."""
import json, re, hashlib
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import urlopen, Request
ROOT = Path(__file__).resolve().parents[1]

def walk(value, key):
    if isinstance(value, dict):
        if key in value: yield value[key]
        for child in value.values(): yield from walk(child, key)
    elif isinstance(value, list):
        for child in value: yield from walk(child, key)

def duration(value):
    if not re.fullmatch(r"\d+(?::\d+){1,2}", value): return 0
    result = 0
    for part in value.split(':'): result = result * 60 + int(part)
    return result

def parse(html, channel):
    marker = re.search(r'(?:var ytInitialData = |ytInitialData"\] = )(\{)', html)
    if not marker: raise ValueError('Missing channel data')
    data, _ = json.JSONDecoder().raw_decode(html[marker.start(1):])
    metadata = data.get('metadata', {}).get('channelMetadataRenderer', {})
    if metadata.get('externalId') != channel['channelId']: raise ValueError('Channel identity mismatch')
    videos = []
    for view in walk(data.get('contents', {}), 'lockupViewModel'):
        if view.get('contentType') != 'LOCKUP_CONTENT_TYPE_VIDEO': continue
        identity = view.get('contentId', '')
        title = view.get('metadata', {}).get('lockupMetadataViewModel', {}).get('title', {}).get('content', '')
        lengths = [duration(b.get('text', '')) for b in walk(view.get('contentImage', {}), 'thumbnailBadgeViewModel')]
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', identity) or not title or max(lengths, default=0) < 600: continue
        if re.search(r'预告|預告|trailer|花絮|behind the scenes', title, re.I): continue
        names = re.findall(r'《([^》]+)》', title)
        # A bracketed official programme name can group episodes safely. Keep other upload titles intact.
        name = names[0].strip() if len(set(names)) == 1 else title
        ep = re.search(r'(?:EP\s*|第)(\d+)(?:[-–]([0-9]+))?(?:集)?', title, re.I)
        episode = ('第' + ep.group(1) + (('-' + ep.group(2)) if ep.group(2) else '') + '集') if ep else title
        videos.append(dict(id=identity, title=title, programme=name, episode=episode,
            category=channel['category'], channelId=channel['channelId'], channelName=channel['name'],
            duration=max(lengths), poster='https://i.ytimg.com/vi/' + identity + '/hqdefault.jpg'))
    if not videos: raise ValueError('No long-form videos; retain previous catalogue')
    return videos

def main():
    target=ROOT/'youtube.json'
    old=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {'videos': []}
    by_id={v['id']:v for v in old['videos']}
    success=0
    for channel in json.loads((ROOT/'youtube-channels.json').read_text(encoding='utf-8')):
        try:
            request=Request('https://www.youtube.com/@'+channel['handle']+'/videos', headers={'User-Agent':'Mozilla/5.0', 'Accept-Language':'zh-CN,zh;q=0.9'})
            with urlopen(request,timeout=30) as response: html=response.read(8*1024*1024+1).decode('utf-8')
            if len(html)>8*1024*1024: raise ValueError('Page too large')
            rows=parse(html,channel)
            for video in rows: by_id[video['id']]=video
            success+=1
            print(channel['id'],len(rows),'videos')
        except Exception as error: print(channel['id'],'retained:',str(error))
    if not success: raise RuntimeError('No channel updated; keep last good catalogue')
    result=dict(schemaVersion=1,updatedAt=datetime.now(timezone.utc).isoformat(),videos=list(by_id.values())[-3000:])
    temp=target.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(target)
if __name__=='__main__': main()
