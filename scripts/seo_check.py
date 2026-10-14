#!/usr/bin/env python3
"""Check what crawlers get from the storefront: SSR html, status codes, redirects.

Plain HTTP, no browser: Google reads the server-rendered html, so this sees what
it sees. Three passes:

  pages    every url in the sitemap: 200, self canonical, indexable, one H1,
           title + description present, og:title/og:description/og:url equal
           to them, JSON-LD that parses. Duplicate titles/descriptions are
           reported too.
  legacy   every old url in the backend's redirect map: one 301, straight to
           a page that answers 200.
  junk     made-up urls: 404, never a 200 page.

Usage (local):
  scripts/seo_check.py --base http://localhost:4011 \\
                       --legacy-json http://localhost:8069/legacy-urls.json
  staging: --base https://dev.silverhorn.co.uk --legacy-json https://dev-odoo.silverhorn.co.uk/legacy-urls.json --staging
  prod:    --base https://silverhorn.co.uk --legacy-json https://odoo.silverhorn.co.uk/legacy-urls.json

Exit code 1 when any check fails. stdlib only.
"""
import argparse
import collections
import concurrent.futures
import html
import json
import random
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = 'Mozilla/5.0 (compatible; SilverHornSEOCheck/1.0)'
JUNK = ['/this-page-does-not-exist', '/model/no-such-model', '/catalog/no-such-make',
        '/parts/no-such-make/no-such-part', '/article/no-such-article', '/brochure/old-format-1',
        '/product/never-existed-0']


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def fetch(url, timeout=60):
    """(status, headers, body) without following redirects."""
    request = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with _opener.open(request, timeout=timeout) as response:
            return response.status, response.headers, response.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read().decode('utf-8', 'replace')
    except Exception as error:  # timeouts, refused connections
        return 0, {}, str(error)


def _attr(head, pattern):
    match = re.search(pattern, head, re.S | re.I)
    return html.unescape(match.group(1)).strip() if match else None


def check_page(base, origin, path, staging):
    """Problems with one sitemap page, plus its title/description for the duplicate check."""
    status, headers, body = fetch(base + path)
    if status != 200:
        return [f'status {status}'], None, None
    problems = []
    head = body.split('</head>')[0]
    title = _attr(head, r'<title>(.*?)</title>')
    description = _attr(head, r'<meta name="description" content="([^"]*)"')
    canonical = _attr(head, r'<link rel="canonical" href="([^"]*)"')
    robots = _attr(head, r'<meta name="robots" content="([^"]*)"') or ''
    h1 = re.findall(r'<h1[\s>]', body, re.I)

    if canonical != origin + path:
        problems.append(f'canonical {canonical!r}')
    if 'noindex' in robots:
        problems.append(f'robots {robots!r}')
    header_robots = headers.get('X-Robots-Tag', '') if headers else ''
    if 'noindex' in header_robots and not staging:
        problems.append(f'X-Robots-Tag {header_robots!r}')
    if len(h1) != 1:
        problems.append(f'{len(h1)} h1')
    if not title:
        problems.append('no title')
    if not description:
        problems.append('no description')
    if _attr(head, r'property="og:title" content="([^"]*)"') != title:
        problems.append('og:title != title')
    if _attr(head, r'property="og:description" content="([^"]*)"') != description:
        problems.append('og:description != description')
    if _attr(head, r'property="og:url" content="([^"]*)"') != canonical:
        problems.append('og:url != canonical')
    for block in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', body, re.S):
        try:
            json.loads(block)
        except ValueError:
            problems.append('JSON-LD does not parse')
    return problems, title, description


def check_legacy(base, old, target):
    status, headers, _ = fetch(base + urllib.parse.quote(old, safe='/,'))
    location = headers.get('Location') if headers else None
    if status != 301:
        return [f'status {status} (expected 301 -> {target})']
    moved_to = urllib.parse.urlsplit(location or '').path
    if moved_to != target:
        return [f'301 to {location!r}, expected {target}']
    final, _, _ = fetch(base + target)
    return [] if final == 200 else [f'target {target} answers {final} (not one hop to a page)']


def check_junk(base, path):
    status, _, _ = fetch(base + path)
    return [] if status == 404 else [f'status {status} (expected 404)']


def run(name, jobs, workers):
    """Run (label, fn, args) jobs; return {label: problems} for the failing ones."""
    failures = {}
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        futures = {pool.submit(fn, *args): label for label, fn, args in jobs}
        for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
            problems = future.result()
            if problems:
                failures[futures[future]] = problems
            if done % 500 == 0:
                print(f'  {name}: {done}/{len(jobs)}', file=sys.stderr)
    return failures


def report(name, total, failures, show):
    print(f'\n{name}: {total - len(failures)}/{total} ok')
    # Group by the kind of problem: drop the quoted values and details.
    by_problem = collections.Counter(re.sub(r" ?['(].*", '', p) for problems in failures.values() for p in problems)
    for problem, count in by_problem.most_common():
        print(f'  {count:6}  {problem}')
    for label, problems in list(failures.items())[:show]:
        print(f'    {label}: {"; ".join(problems)}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base', required=True, help='storefront to check, e.g. http://localhost:4011')
    parser.add_argument('--legacy-json', help='backend redirect map, e.g. http://localhost:8069/legacy-urls.json')
    parser.add_argument('--origin', default='https://silverhorn.co.uk', help='public origin in sitemap/canonicals')
    parser.add_argument('--limit', type=int, help='check a random sample of this many sitemap/legacy urls')
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--show', type=int, default=10, help='failing urls listed per pass')
    parser.add_argument('--staging', action='store_true', help='X-Robots-Tag: noindex is expected')
    args = parser.parse_args()
    base, origin = args.base.rstrip('/'), args.origin.rstrip('/')
    sample = (lambda items: random.sample(items, min(args.limit, len(items)))) if args.limit else list

    status, _, sitemap = fetch(base + '/sitemap.xml')
    if status != 200:
        sys.exit(f'sitemap.xml: status {status}')
    paths = [urllib.parse.urlsplit(html.unescape(loc)).path or '/'
             for loc in re.findall(r'<loc>([^<]+)</loc>', sitemap)]
    print(f'sitemap: {len(paths)} urls')

    pages = sample(paths)
    titles, descriptions = collections.defaultdict(list), collections.defaultdict(list)

    def page_and_collect(path):
        problems, title, description = check_page(base, origin, path, args.staging)
        if title:
            titles[title].append(path)
        if description:
            descriptions[description].append(path)
        return problems

    failures = run('pages', [(path, page_and_collect, (path,)) for path in pages], args.workers)
    report('pages', len(pages), failures, args.show)
    for name, seen in (('titles', titles), ('descriptions', descriptions)):
        dupes = {text: urls for text, urls in seen.items() if len(urls) > 1}
        print(f'  duplicate {name}: {len(dupes)} texts on {sum(map(len, dupes.values()))} pages')
        for text, urls in list(dupes.items())[:3]:
            print(f'    {text[:70]!r}: {", ".join(urls[:3])}')
    failed = bool(failures)

    if args.legacy_json:
        status, _, body = fetch(args.legacy_json)
        if status != 200:
            sys.exit(f'{args.legacy_json}: status {status}')
        redirects = json.loads(body)
        old = sample(sorted(redirects))
        failures = run('legacy', [(path, check_legacy, (base, path, redirects[path])) for path in old], args.workers)
        report('legacy (one 301 to a live page)', len(old), failures, args.show)
        failed |= bool(failures)

    failures = run('junk', [(path, check_junk, (base, path)) for path in JUNK], args.workers)
    report('junk (404)', len(JUNK), failures, args.show)
    failed |= bool(failures)

    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
