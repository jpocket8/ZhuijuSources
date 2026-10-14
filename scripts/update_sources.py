"""Build a data-only source manifest; never execute TVBox plugins."""
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 8 * 1024 * 1024

def https(url):
    parsed = urlsplit(url)
    return parsed.scheme == 'https' and bool(parsed.hostname) and not parsed.username and not parsed.password

def parse_config(text):
    # Preserve quoted URLs while accepting TVBox JSON comments and trailing commas.
    text = re.sub(r'"(?:\\.|[^"\\])*"|//[^\r\n]*|/\*[\s\S]*?\*/',
                  lambda m: m.group() if m.group().startswith('"') else ' ', text)
    text = re.sub(r'"(?:\\.|[^"\\])*"|,\s*(?=[}\]])',
                  lambda m: m.group() if m.group().startswith('"') else '', text)
    return json.loads(text)

def fetch(url):
    if not https(url):
        raise ValueError('Only HTTPS addresses are supported')
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'ZhuijuSources/1.0'}), timeout=30) as response:
                if not https(response.url):
                    raise ValueError('Unsafe redirect')
                data = response.read(LIMIT + 1)
                if len(data) > LIMIT:
                    raise ValueError('Response too large')
                return parse_config(data.decode('utf-8-sig'))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))

def extract(config, address, upstream):
    sites = config.get('sites')
    if not isinstance(sites, list) or not sites:
        raise ValueError('Missing upstream sites')
    rows = []
    for site in sites:
        if not isinstance(site, dict) or str(site.get('type')) != '1':
            continue
        api = site.get('api')
        if not isinstance(api, str) or not api.strip():
            continue
        url = urljoin(address, api.strip())
        if not https(url):
            continue
        rows.append(dict(id=upstream['id'] + ':' + hashlib.sha256(url.encode()).hexdigest()[:16],
                         name=upstream['name'] + ' · ' + str(site.get('name') or '未命名片源'),
                         kind='json-vod', url=url, upstream=upstream['id'],
                         canSearch=str(site.get('searchable', 1)) != '0'))
    if not rows:
        raise ValueError('No compatible sources; retain last published manifest')
    return rows

def build(settings, fetcher=fetch, live_fetcher=None):
    catalog = fetcher(settings['catalog'])
    directory = {r['id']: r for r in catalog['resources']}
    rows = list(settings['pinned'])
    origins = []
    live_artifacts = {}
    live_skipped = 0
    live_errors = []
    previous_live = {p.name:p.read_text(encoding="utf-8") for p in (ROOT/"live").glob("*.m3u")}
    from tvbox_live import extract as extract_live, fetch_text
    for identity in settings['upstreams']:
        upstream = directory[identity]
        address = upstream['url']
        config = fetcher(address)
        if config.get('sites'):
            rows.extend(extract(config, address, upstream))
        live, files, skipped = extract_live(config, address, upstream, live_fetcher or fetch_text, previous_live, live_errors)
        rows.extend(live); live_artifacts.update(files); live_skipped += skipped
        origins.append(dict(id=identity, name=upstream['name'], url=address))
    for subscription in settings.get('liveSubscriptions', []):
        address = subscription['url']
        upstream = dict(id='live-subscription:'+hashlib.sha256(address.encode()).hexdigest()[:16],name=subscription['name'])
        config = fetcher(address)
        live, files, skipped = extract_live(config, address, upstream, live_fetcher or fetch_text, previous_live, live_errors)
        rows.extend(live); live_artifacts.update(files); live_skipped += skipped
        origins.append(dict(id=upstream['id'],name=upstream['name'],url=address))
    # Append optional live lists so existing source numbering is preserved.
    rows.extend(settings.get("additionalSources", []))
    result = []
    seen = set()
    for row in rows:
        url = row['url']
        if url in settings.get('disabledUrls', []) or url in seen:
            continue
        if not https(url) or row['kind'] not in ('json-vod', 'm3u'):
            raise ValueError('Invalid source')
        seen.add(url)
        result.append(row)
    if not result or len(result) > 500 or len({r['id'] for r in result}) != len(result):
        raise ValueError('Invalid source count or duplicate IDs')
    return dict(schemaVersion=1, updatedAt=datetime.now(timezone.utc).isoformat(),
                attribution=dict(name='awesome-zhuiju-free', author='laoma2053 and contributors',
                                 url='https://github.com/laoma2053/awesome-zhuiju-free',
                                 license='CC-BY-4.0', changes='Selected and normalized standard HTTPS interfaces; added app metadata'),
                upstreams=origins, sources=result, liveImport=dict(skipped=live_skipped, playlists=len(live_artifacts), errors=live_errors), _liveArtifacts=live_artifacts)

def main():
    settings = json.loads((ROOT / 'settings.json').read_text(encoding='utf-8'))
    manifest = build(settings)  # Do not replace last good file if ANY upstream fails.
    manifest['youtubeChannels'] = json.loads((ROOT / 'youtube-channels.json').read_text(encoding='utf-8'))
    for name, content in manifest.pop('_liveArtifacts').items():
        folder = ROOT / 'live'; folder.mkdir(exist_ok=True)
        pending = folder / (name+'.tmp'); pending.write_text(content,encoding='utf-8'); pending.replace(folder/name)
    target = ROOT / 'sources.json'
    temp = target.with_suffix('.tmp')
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(target)
    print(f'Published {len(manifest["sources"])} compatible sources (playback not verified).')

if __name__ == '__main__':
    main()
