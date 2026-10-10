"""One scheduled collector for public Release download counts and display metadata."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
NOW = lambda: datetime.now(timezone.utc).isoformat()


def api(path):
    headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'laoyu-release-stats',
               'X-GitHub-Api-Version': '2022-11-28'}
    if os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urlopen(Request('https://api.github.com/repos/' + path, headers=headers), timeout=25) as response:
        return json.load(response)


def release_list(repo, getter=api):
    rows, page = [], 1
    while True:
        batch = getter(f'{repo}/releases?per_page=100&page={page}')
        if not isinstance(batch, list):
            raise ValueError('Release list must be an array')
        rows.extend(r for r in batch if not r.get('draft'))
        if len(batch) < 100:
            return rows
        page += 1


def matched(product, release):
    assets = [a for a in release['assets'] if
              (a['name'] == product['assetName'] if product.get('assetName') else
               a['name'].startswith(product['assetPrefix']) and a['name'].endswith(product['assetSuffix']))]
    if len(assets) > 1:
        raise ValueError('Ambiguous platform assets')
    return assets[0] if assets else None


def display_release(product, rows, getter, at):
    if product.get('includePrereleases'):
        release = next((r for r in rows if matched(product, r)), None)
    else:
        # Preserve GitHub /latest semantics instead of guessing from tag order.
        release = getter(product['releaseRepo'] + '/releases/latest')
    if not release or release.get('draft') or (release.get('prerelease') and not product.get('includePrereleases')):
        return None
    asset = matched(product, release)
    if not asset:
        return None
    digest = asset.get('digest') or ''
    return {'version': release['tag_name'].removeprefix('v'), 'name': asset['name'],
            'url': asset['browser_download_url'], 'sha256': digest[7:] if digest.startswith('sha256:') else None,
            'page': release['html_url'], 'notes': str(release.get('name') or '')[:160],
            'prerelease': bool(release.get('prerelease')), 'checkedAt': at}


def collect(products, previous=None, getter=api, at=None):
    at = at or NOW()
    old = {p['id']: p for p in (previous or {}).get('products', []) + (previous or {}).get('additionalStats', [])}
    cache, result = {}, []
    for product in products:
        identifier, repo = product['id'], product.get('statsRepo') or product.get('releaseRepo')
        if not repo:
            result.append({'id': identifier, 'repository': None, 'count': None,
                           'status': 'untracked', 'updatedAt': None, 'latestRelease': None})
            continue
        try:
            if repo not in cache:
                cache[repo] = release_list(repo, getter)
            rows = cache[repo]
            seen, total = set(), 0
            # Keep historical/old-client downloads after a public brand migration.
            # Repositories share the cache; repeated repository entries count once.
            repositories = list(dict.fromkeys([repo] + product.get('additionalStatsRepos', [])))
            for source in repositories:
                if source not in cache:
                    cache[source] = release_list(source, getter)
                for release in cache[source]:
                    for asset in release['assets']:
                        key, count = (source, asset['id']), asset['download_count']
                        if key in seen or type(count) is not int or count < 0:
                            raise ValueError('Invalid or duplicate asset')
                        seen.add(key)
                        total += count
            latest = None
            try:
                if product.get('releaseRepo'):
                    latest = display_release(product, rows, getter, at)
            except Exception as error:
                print(f'{identifier}: version display unavailable ({type(error).__name__})')
            result.append({'id': identifier, 'repository': repo, 'count': total,
                           'status': 'ok', 'updatedAt': at, 'latestRelease': latest})
        except Exception as error:
            before = old.get(identifier)
            if before and before.get('repository') == repo and isinstance(before.get('count'), int):
                result.append({**before, 'status': 'stale'})
            else:
                result.append({'id': identifier, 'repository': repo, 'count': None,
                               'status': 'unavailable', 'updatedAt': None, 'latestRelease': None})
            print(f'{identifier}: collection failed ({type(error).__name__}); retained previous data')
    # Old clients require every positive count to have a desktop releaseRepo.
    # Keep their original products array valid, and add statistics-only sources
    # separately. New clients merge these overrides; one fetch still suffices.
    stats_only = {p['id'] for p in products if p.get('statsRepo') and not p.get('releaseRepo')}
    extra = [row for row in result if row['id'] in stats_only]
    legacy = [row if row['id'] not in stats_only else
              {'id': row['id'], 'repository': None, 'count': None, 'status': 'untracked',
               'updatedAt': None, 'latestRelease': None} for row in result]
    return {'schemaVersion': 1, 'metric': 'github_release_asset_downloads',
            'generatedAt': at, 'products': legacy, 'additionalStats': extra}


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def main():
    products = json.loads((ROOT/'products.json').read_text(encoding='utf-8'))
    target = ROOT/'docs/stats/downloads.json'
    previous = json.loads(target.read_text(encoding='utf-8')) if target.exists() else None
    result = collect(products, previous)
    merged = {p['id']: p for p in result['products'] + result['additionalStats']}
    if not any(p['status'] == 'ok' for p in merged.values()):
        raise RuntimeError('No repositories collected successfully; keep previous published files')
    history_path = ROOT/'docs/stats/history.json'
    history = json.loads(history_path.read_text(encoding='utf-8')) if history_path.exists() else []
    day = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    snapshots = {row['date']: row for row in history}
    snapshots[day] = {'date': day, 'products': [{k: p[k] for k in ('id', 'count', 'status', 'updatedAt')} for p in merged.values()]}
    atomic(target, result)
    atomic(history_path, [snapshots[key] for key in sorted(snapshots)][-730:])
    for row in merged.values():
        print(f'{row["id"]}: {row["count"]} ({row["status"]})')


if __name__ == '__main__':
    main()
