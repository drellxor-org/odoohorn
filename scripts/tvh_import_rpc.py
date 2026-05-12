#!/usr/bin/env python3
"""Import the CSVs produced by tvh_to_odoo.py into Odoo via XML-RPC.

Uses each model's `load()` method which is what the Odoo UI uses internally for CSV imports.
External IDs in the `id` column make the import idempotent (re-running upserts).

Image binaries are loaded in a separate pass: the manifest CSV maps reference → filename,
the script reads each file from the images directory, base64-encodes it, and writes
image_1920 on the matching product.template.

Usage:
  tvh_import_rpc.py \\
    --url http://localhost:8069 \\
    --db silverhorn_prod \\
    --user admin \\
    --password admin \\
    --csv-dir /path/to/output \\
    --images-dir /path/to/images
"""

import argparse
import base64
import csv
import os
import re
import sys
import xmlrpc.client
from pathlib import Path


IMPORT_ORDER = [
    ('02_product_make.csv', 'product.make'),
    ('03_product_public_category.csv', 'product.public.category'),
    ('04_product_template.csv', 'product.template'),
    ('05_product_application.csv', 'product.application'),
]


def connect(url, db, user, password):
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, user, password, {})
    if not uid:
        raise SystemExit(f'Authentication failed for {user}@{db}')
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
    return uid, models


def execute(models, db, uid, password, model, method, *args, **kwargs):
    return models.execute_kw(db, uid, password, model, method, list(args), kwargs)


def load_csv(models, db, uid, password, model, path):
    """Read a CSV produced by tvh_to_odoo.py and call model.load()."""
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return {'ids': [], 'messages': []}
    fields = rows[0]
    data = rows[1:]
    print(f'  loading {len(data)} rows into {model}...', file=sys.stderr, flush=True)
    return execute(models, db, uid, password, model, 'load', fields, data)


def import_csvs(models, db, uid, password, csv_dir, batch_size):
    csv_dir = Path(csv_dir)
    for filename, model in IMPORT_ORDER:
        path = csv_dir / filename
        if not path.exists():
            print(f'skip {filename} (not found)', file=sys.stderr)
            continue
        print(f'== {filename} -> {model}', file=sys.stderr)
        # batch large files to avoid huge single calls
        with path.open(newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            continue
        fields = rows[0]
        data = rows[1:]
        total_ok = 0
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            result = execute(models, db, uid, password, model, 'load', fields, batch)
            ids = result.get('ids') or []
            messages = result.get('messages') or []
            ok = len([x for x in ids if x])
            total_ok += ok
            if messages:
                print(f'  batch {i // batch_size}: {ok}/{len(batch)} ok, {len(messages)} messages',
                      file=sys.stderr)
                for m in messages[:5]:
                    print(f'    {m.get("type", "?")}: {m.get("message", "")} '
                          f'(record {m.get("record", "?")})', file=sys.stderr)
                if len(messages) > 5:
                    print(f'    ... {len(messages) - 5} more', file=sys.stderr)
            else:
                print(f'  batch {i // batch_size}: {ok}/{len(batch)} ok', file=sys.stderr)
        print(f'  total: {total_ok}/{len(data)} into {model}', file=sys.stderr)


def _tokenize(s):
    return set(t for t in re.findall(r'[a-z0-9]+', (s or '').lower()) if t)


def match_brochures(models, db, uid, password, min_tokens=2):
    """Heuristic match: applications without brochure_id get linked to a brochure whose
    name tokens (alphanumeric, lowercase) are a subset of (make.name + ' ' + model + ' ' + serie)
    tokens. If multiple brochures match, the one with the most tokens wins (most specific).
    Ties yield no link.

    Brochures with fewer than `min_tokens` tokens are skipped to avoid trivial single-token
    matches.
    """
    brochures = execute(models, db, uid, password, 'brochure', 'search_read',
                        [], fields=['id', 'name'])
    candidates = []
    for b in brochures:
        toks = _tokenize(b.get('name'))
        if len(toks) >= min_tokens:
            candidates.append((b['id'], b['name'], toks))
    print(f'== brochure matcher: {len(candidates)} candidate brochures (>= {min_tokens} tokens)',
          file=sys.stderr)
    if not candidates:
        return

    apps = execute(models, db, uid, password, 'product.application', 'search_read',
                   [('brochure_id', '=', False)],
                   fields=['id', 'make_id', 'model', 'serie'])
    if not apps:
        print('  no unmatched applications', file=sys.stderr)
        return

    # resolve make names in one batch
    make_ids = sorted({a['make_id'][0] for a in apps if a.get('make_id')})
    make_names = {m['id']: m['name'] for m in execute(
        models, db, uid, password, 'product.make', 'search_read',
        [('id', 'in', make_ids)], fields=['id', 'name'])} if make_ids else {}

    linked = 0
    ambiguous = 0
    unmatched = 0
    for app in apps:
        make_name = make_names.get(app['make_id'][0]) if app.get('make_id') else ''
        haystack = _tokenize(' '.join(filter(None, [make_name, app.get('model'), app.get('serie')])))
        if not haystack:
            unmatched += 1
            continue
        best = []
        best_size = 0
        for bid, bname, toks in candidates:
            if toks.issubset(haystack):
                if len(toks) > best_size:
                    best = [(bid, bname)]
                    best_size = len(toks)
                elif len(toks) == best_size:
                    best.append((bid, bname))
        if len(best) == 1:
            execute(models, db, uid, password, 'product.application', 'write',
                    [app['id']], {'brochure_id': best[0][0]})
            linked += 1
        elif len(best) > 1:
            ambiguous += 1
        else:
            unmatched += 1
        if (linked + ambiguous + unmatched) % 500 == 0:
            print(f'  progress: linked={linked} ambiguous={ambiguous} unmatched={unmatched}',
                  file=sys.stderr, flush=True)
    print(f'brochure match: linked={linked}, ambiguous={ambiguous}, unmatched={unmatched}',
          file=sys.stderr)


def import_images(models, db, uid, password, csv_dir, images_dir):
    manifest = Path(csv_dir) / '06_image_manifest.csv'
    if not manifest.exists():
        print('skip image manifest (not found)', file=sys.stderr)
        return
    images_dir = Path(images_dir)
    if not images_dir.is_dir():
        raise SystemExit(f'images directory not found: {images_dir}')

    with manifest.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return

    # map default_code -> id once
    refs = sorted({r['reference'] for r in rows if r.get('reference')})
    print(f'== images: {len(rows)} entries, looking up {len(refs)} product.template ids', file=sys.stderr)
    found = execute(models, db, uid, password, 'product.template', 'search_read',
                    [('default_code', 'in', refs)], fields=['id', 'default_code'])
    by_ref = {r['default_code']: r['id'] for r in found}

    ok = 0
    missing_files = 0
    missing_products = 0
    for row in rows:
        ref = row.get('reference')
        filename = row.get('filename')
        if not (ref and filename):
            continue
        tmpl_id = by_ref.get(ref)
        if not tmpl_id:
            missing_products += 1
            continue
        img_path = images_dir / filename
        if not img_path.is_file():
            missing_files += 1
            continue
        with img_path.open('rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        execute(models, db, uid, password, 'product.template', 'write',
                [tmpl_id], {'image_1920': data})
        ok += 1
        if ok % 50 == 0:
            print(f'  {ok} images written...', file=sys.stderr, flush=True)
    print(f'images: {ok} written, {missing_files} files missing, {missing_products} products missing',
          file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description='Import TVH-converted CSVs into Odoo via XML-RPC.')
    ap.add_argument('--url', default=os.environ.get('ODOO_URL', 'http://localhost:8069'))
    ap.add_argument('--db', default=os.environ.get('ODOO_DB'))
    ap.add_argument('--user', default=os.environ.get('ODOO_USER', 'admin'))
    ap.add_argument('--password', default=os.environ.get('ODOO_PASSWORD', 'admin'))
    ap.add_argument('--csv-dir', required=True)
    ap.add_argument('--images-dir', help='Directory holding image files referenced in 06_image_manifest.csv')
    ap.add_argument('--batch-size', type=int, default=500)
    ap.add_argument('--skip-images', action='store_true')
    ap.add_argument('--skip-brochure-match', action='store_true',
                    help='Skip the post-import brochure auto-match for product.application.')
    ap.add_argument('--brochure-min-tokens', type=int, default=2,
                    help='Ignore brochures whose name has fewer than N alphanumeric tokens (default 2).')
    args = ap.parse_args()

    if not args.db:
        raise SystemExit('--db is required (or set ODOO_DB)')

    uid, models = connect(args.url, args.db, args.user, args.password)
    print(f'Connected to {args.url} as uid={uid}', file=sys.stderr)

    import_csvs(models, args.db, uid, args.password, args.csv_dir, args.batch_size)

    if not args.skip_brochure_match:
        match_brochures(models, args.db, uid, args.password,
                        min_tokens=args.brochure_min_tokens)

    if not args.skip_images and args.images_dir:
        import_images(models, args.db, uid, args.password, args.csv_dir, args.images_dir)
    elif not args.skip_images:
        print('NOTE: --images-dir not provided; skipping image import', file=sys.stderr)


if __name__ == '__main__':
    main()
