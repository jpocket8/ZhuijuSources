"""Traverse data-only TVBox stores. Never load spider/JAR/JS implementations."""
import hashlib
import time
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def canonical(value, base=''):
    address = urljoin(base, value.strip())
    for proxy in ('https://gh-proxy.com/', 'https://ghproxy.net/', 'https://github.moeyy.xyz/'):
        if address.startswith(proxy + 'https://raw.githubusercontent.com/'):
            address = address[len(proxy):]
    p = urlsplit(address)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Unsupported subscription URL')
    # Only import a plaintext-listed endpoint if its HTTPS counterpart works.
    host = p.hostname.encode('idna').decode('ascii')
    if p.port:
        host += ':' + str(p.port)
    return urlunsplit(('https', host, quote(p.path, safe='/%:@'), p.query, ''))


def fetch_config(address):
    from update_sources import parse_config, https, LIMIT
    with urlopen(Request(address, headers={'User-Agent': 'ZhuijuSources/1.0'}), timeout=8) as response:
        if not https(response.url):
            raise ValueError('Non-HTTPS redirect')
        body = response.read(LIMIT + 1)
        if len(body) > LIMIT:
            raise ValueError('Response too large')
        return parse_config(body.decode('utf-8-sig'))


def discover(subscriptions, fetcher=fetch_config, limit=40, budget=180):
    queue = [(s['url'], s['name'], 0, '') for s in subscriptions]
    seen, configs, errors = set(), [], []
    started = time.monotonic()
    while queue and len(seen) < limit and time.monotonic() - started < budget:
        value, name, depth, base = queue.pop(0)
        try:
            address = canonical(value, base)
            if address in seen:
                continue
            seen.add(address)
            config = fetcher(address)
            if not isinstance(config, dict):
                raise ValueError('Configuration must be an object')
            if config.get('sites') or config.get('lives'):
                upstream = dict(id='tvbox:'+hashlib.sha256(address.encode()).hexdigest()[:16], name=name, url=address)
                configs.append((config, address, upstream))
            children = []
            for field in ('storeHouse', 'urls'):
                values = config.get(field, [])
                if isinstance(values, list):
                    children.extend(values)
            if depth < 3:
                for child in children:
                    if not isinstance(child, dict):
                        continue
                    link = child.get('sourceUrl') or child.get('url')
                    if isinstance(link, str) and (link.startswith(('https://', 'http://', './', '../', '/'))):
                        queue.append((link, str(child.get('sourceName') or child.get('name') or name), depth+1, address))
        except Exception as error:
            errors.append(dict(url=value, error=str(error)))
    if queue:
        errors.append(dict(error='Traversal limit reached', remaining=len(queue)))
    return configs, dict(visited=len(seen), configurations=len(configs), errors=errors)


def validate_vod(rows, fetcher=fetch_config):
    """Require a standard catalog response before adding newly discovered APIs."""
    from concurrent.futures import ThreadPoolExecutor
    from urllib.parse import parse_qsl, urlencode
    def check(row):
        p = urlsplit(row['url'])
        query = dict(parse_qsl(p.query, keep_blank_values=True))
        query.update(ac='detail', pg='1')
        address = urlunsplit((p.scheme, p.netloc, p.path, urlencode(query), ''))
        try:
            result = fetcher(address)
            entries = result.get('list') if isinstance(result, dict) else None
            if not isinstance(entries, list) or not entries or not all(isinstance(item, dict) and item.get('vod_id') is not None and item.get('vod_name') for item in entries):
                raise ValueError('No standard VOD catalog entries')
            return row, None
        except Exception as error:
            return None, dict(url=row['url'], error=str(error))
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(check, rows))
    return [row for row, error in results if row], [error for row, error in results if error]


def source_key(address):
    from urllib.parse import parse_qsl, urlencode
    p = urlsplit(address)
    query = sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not (k == 'ac' and v in ('list', 'detail')))
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip('/'), urlencode(query), ''))
