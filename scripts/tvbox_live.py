"""Independent, data-only TVBOX live import. Never loads parsers or plugins."""
import hashlib
import re
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

LIMIT = 8 * 1024 * 1024

def safe_url(value, base='', subscription=False):
    if not isinstance(value, str):
        return None
    value = urljoin(base, value.strip())
    try:
        p = urlsplit(value)
        if p.scheme not in (('https',) if subscription else ('https', 'http')) or not p.hostname or p.username or p.password:
            return None
        if any(ord(c) < 32 for c in value):
            return None
        return value
    except ValueError:
        return None

def fetch_text(url):
    if not safe_url(url, subscription=True):
        raise ValueError('Live subscription must use HTTPS')
    with urlopen(Request(url, headers={'User-Agent': 'TuaoTV-SourceUpdater/1'}), timeout=20) as response:
        if not safe_url(response.url, subscription=True):
            raise ValueError('Invalid live subscription redirect')
        data = response.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError('Live subscription too large')
        return data.decode('utf-8-sig')

def label(value):
    return re.sub(r'[\r\n"<>]', '', str(value or '')).strip()[:200]

def playlist(channels):
    lines = ['#EXTM3U']; seen = set()
    for row in channels:
        name = label(row.get('name'))
        for raw in row.get('urls', []):
            url = safe_url(raw)
            if not name or not url or (name, url) in seen:
                continue
            seen.add((name, url))
            if len(seen) > 20000:
                raise ValueError('Too many live channels')
            attrs = ' '.join(f'{key}="{label(row.get(field))}"' for key, field in [('group-title','group'),('tvg-id','id'),('tvg-logo','logo'),('tvg-country','country')])
            lines.append(f'#EXTINF:-1 {attrs},{name}')
            for key in ('http-user-agent','http-referrer'):
                if row.get(key): lines.append('#EXTVLCOPT:'+key+'='+label(row[key]))
            lines.append(url)
    if not seen:
        raise ValueError('No compatible live channels')
    return '\n'.join(lines) + '\n'

def from_text(text, base):
    if len(text.encode()) > LIMIT:
        raise ValueError('Live playlist too large')
    rows = []; group = ''; current = None
    for line in text.lstrip('\ufeff').splitlines():
        line = line.strip()
        if line.startswith('#EXTINF:'):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', line))
            # Commas inside quoted attributes are not channel delimiters.
            match = re.match(r'#EXTINF:(?:"[^"]*"|[^",])*,(.*)', line)
            current = dict(name=match.group(1) if match else '', group=attrs.get('group-title',''), id=attrs.get('tvg-id',''), country=attrs.get('tvg-country',''), logo=attrs.get('tvg-logo',''), urls=[], **{k:attrs[k] for k in ('http-user-agent','http-referrer') if k in attrs})
        elif current is not None and line.startswith('#EXTVLCOPT:'):
            key, _, value = line[len('#EXTVLCOPT:'):].partition('=')
            if key in ('http-user-agent','http-referrer'): current[key] = value
        elif line.startswith('#') or not line:
            continue
        elif current is not None:
            url = safe_url(line, base)
            if url:
                current['urls'] = [url]; rows.append(current)
            current = None
        elif ',' in line:
            name, value = line.split(',', 1)
            if value.strip() == '#genre#':
                group = name
            else:
                urls = [safe_url(v.split('$',1)[0], base) for v in value.split('#')]
                rows.append(dict(name=name, group=group, urls=[u for u in urls if u]))
    return playlist(rows)

def extract(config, address, upstream, fetcher=fetch_text, previous=None, errors=None):
    """Return stable generated playlist names and independent source descriptors."""
    rows = []; artifacts = {}; skipped = 0
    started = time.monotonic()
    lives = config.get('lives', [])
    if not isinstance(lives, list) or len(lives) > 100:
        raise ValueError('Invalid TVBOX live list')
    for index, live in enumerate(lives):
        if not isinstance(live, dict):
            skipped += 1; continue
        name = label(live.get('name') or '直播')
        channels = []
        for group in live.get('groups', []) if isinstance(live.get('groups', []), list) else []:
            if not isinstance(group, dict): continue
            for ch in group.get('channels', []) if isinstance(group.get('channels', []), list) else []:
                if not isinstance(ch, dict): continue
                urls = ch.get('urls', [])
                if isinstance(urls, str): urls = [urls]
                if not isinstance(urls, list): continue
                channels.append(dict(name=ch.get('name'), group=group.get('group') or group.get('name') or name,
                    id=ch.get('tvg-id') or ch.get('id'), country=ch.get('country') or live.get('country'), logo=ch.get('logo'), **{'http-user-agent':ch.get('ua') or live.get('ua'),'http-referrer':ch.get('referer') or live.get('referer')}, urls=[safe_url(u,address) for u in urls]))
        if channels:
            content = playlist(channels); key = address+'#'+name
        else:
            url = safe_url(live.get('url'), address, subscription=True)
            if not url:
                skipped += 1; continue
            key = url
            old_name = 'tvbox-live-' + hashlib.sha256(key.encode()).hexdigest()[:16] + '.m3u'
            try:
                if time.monotonic() - started > 60:
                    raise TimeoutError("Live import time budget reached")
                content = from_text(fetcher(url), url)
            except Exception as error:
                if errors is None: raise
                content = (previous or {}).get(old_name)
                errors.append(dict(source=upstream['name']+' · '+name, error=str(error), retained=bool(content)))
                if not content:
                    skipped += 1; continue
        identity = 'tvbox-live:' + hashlib.sha256(key.encode()).hexdigest()[:16]
        filename = identity.replace(':','-')+'.m3u'
        artifacts[filename] = content
        rows.append(dict(id=identity,name=upstream['name']+' · '+name,kind='m3u',
            url='https://raw.githubusercontent.com/jpocket8/ZhuijuSources/main/live/'+filename,upstream=upstream['id']))
    return rows, artifacts, skipped
