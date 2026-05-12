#!/usr/bin/env python3
"""Convert TVH catalog files into Odoo-loadable CSVs.

Input directory must contain at least the main catalog file. Other files are optional.
Recognised by suffix (case-insensitive):
    *-TLH-catalog.{csv,txt}              main catalog (comma-separated, double-quoted)
    *-TLH-catalog-applications.csv       pipe-separated
    *-TLH-catalog-images.csv             semicolon-separated
    *-TLH-catalog-price_list.csv         semicolon-separated, optional

Output CSVs (in output-dir):
    01_data_source.csv
    02_product_make.csv
    03_product_public_category.csv
    04_product_template.csv
    05_product_application.csv
    06_image_manifest.csv             (reference,filename — RPC script reads bytes)
"""

import argparse
import csv
import hashlib
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path


DATA_SOURCE_CODE = 'TVH'
DATA_SOURCE_NAME = 'TVH'
# Reference the addon-preloaded data.source record instead of creating a new one.
DATA_SOURCE_XMLID = 'product_catalog.data_source_tvh'


def slugify(value):
    s = re.sub(r'[^A-Za-z0-9]+', '_', (value or '').lower()).strip('_')
    return re.sub(r'_+', '_', s) or 'x'


def category_xmlid(path_parts):
    return f"__import__.cat_{DATA_SOURCE_CODE.lower()}_" + '__'.join(slugify(p) for p in path_parts)


def make_xmlid(code):
    return f"__import__.make_{DATA_SOURCE_CODE.lower()}_{slugify(code)}"


def template_xmlid(make_code, reference):
    return f"__import__.tmpl_{DATA_SOURCE_CODE.lower()}_{slugify(make_code)}_{slugify(reference)}"


def application_xmlid(reference, make_code, model, serie, vehicle_type_code):
    key = '|'.join([reference or '', make_code or '', model or '', serie or '', vehicle_type_code or ''])
    return f"__import__.app_{hashlib.sha1(key.encode('utf-8')).hexdigest()[:16]}"


# ---------- File discovery ----------

def find_input_files(input_dir):
    files = {}
    for p in Path(input_dir).iterdir():
        if not p.is_file():
            continue
        lower = p.name.lower()
        if lower.endswith('-tlh-catalog-applications.csv'):
            files['applications'] = p
        elif lower.endswith('-tlh-catalog-images.csv'):
            files['images'] = p
        elif lower.endswith('-tlh-catalog-price_list.csv'):
            files['prices'] = p
        elif 'tlh-catalog' in lower and (lower.endswith('.csv') or lower.endswith('.txt')):
            files['catalog'] = p
    if 'catalog' not in files:
        raise SystemExit(f"No *-TLH-catalog.{{csv,txt}} file found in {input_dir}")
    return files


# ---------- Readers ----------

def read_catalog(path):
    """Catalog file: comma-separated, double-quoted, header row."""
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return [{k.strip(): (v or '').strip() for k, v in row.items()} for row in reader]


def read_pipe(path):
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='|')
        return [{k.strip(): (v or '').strip() for k, v in row.items()} for row in reader]


def read_semicolon(path):
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        return [{k.strip(): (v or '').strip() for k, v in row.items()} for row in reader]


# ---------- Converters ----------

def to_bool(value):
    return str(value).strip().lower() in ('true', '1', 'yes', 'y')


def to_float(value):
    try:
        return float(str(value).replace(',', '.'))
    except (ValueError, TypeError):
        return 0.0


# ---------- Builders ----------

def build_categories(catalog_rows):
    """Walk the rows, return OrderedDict {xmlid: {id, name, parent_id/id}} preserving depth order."""
    nodes = OrderedDict()

    def upsert(path):
        if not path:
            return None
        xmlid = category_xmlid(path)
        if xmlid not in nodes:
            parent_xmlid = category_xmlid(path[:-1]) if len(path) > 1 else ''
            nodes[xmlid] = {
                'id': xmlid,
                'name': path[-1],
                'parent_id/id': parent_xmlid,
            }
        return xmlid

    for row in catalog_rows:
        path = []
        for col in ('Family', 'Subfamily', 'Sub-subfamily'):
            val = row.get(col)
            if val:
                path.append(val)
                upsert(path)
    return nodes


def build_makes(catalog_rows):
    """Return OrderedDict {xmlid: {id, code, name, data_source_id/id}}."""
    makes = OrderedDict()
    for row in catalog_rows:
        code = row.get('make')
        if not code:
            continue
        xmlid = make_xmlid(code)
        if xmlid not in makes:
            makes[xmlid] = {
                'id': xmlid,
                'code': code,
                'name': row.get('make_description') or code,
                'data_source_id/id': DATA_SOURCE_XMLID,
            }
    return makes


def build_templates(catalog_rows, prices_by_ref):
    """Return list of dicts for product.template."""
    out = []
    for row in catalog_rows:
        make_code = row.get('make') or ''
        reference = row.get('reference') or ''
        if not (make_code and reference):
            continue
        # deepest category present
        deepest_path = []
        for col in ('Family', 'Subfamily', 'Sub-subfamily'):
            val = row.get(col)
            if val:
                deepest_path.append(val)
        cat_xmlid = category_xmlid(deepest_path) if deepest_path else ''

        weight_gr = to_float(row.get('weight_gr'))
        length_mm = to_float(row.get('length_mm'))
        width_mm = to_float(row.get('width_mm'))
        height_mm = to_float(row.get('height_mm'))

        record = {
            'id': template_xmlid(make_code, reference),
            'name': row.get('description') or reference,
            'default_code': reference,
            'data_source_id/id': DATA_SOURCE_XMLID,
            'make_id/id': make_xmlid(make_code),
            'is_dangerous_goods': '1' if to_bool(row.get('dangerous_goods')) else '0',
            'weight_gr': weight_gr,
            'length_mm': length_mm,
            'width_mm': width_mm,
            'height_mm': height_mm,
            'weight': round(weight_gr / 1000.0, 6),
            'public_categ_ids/id': cat_xmlid,
            'sale_ok': '1',
            'purchase_ok': '1',
            'type': 'product',
        }
        if reference in prices_by_ref:
            record['list_price'] = prices_by_ref[reference]
        out.append(record)
    return out


def build_applications(application_rows):
    out = []
    seen = set()
    for row in application_rows:
        ref = row.get('Reference') or ''
        make_code = row.get('Make') or ''
        if not (ref and make_code):
            continue
        model = row.get('model') or row.get('Model') or ''
        serie = row.get('serie') or row.get('Serie') or ''
        vtc = row.get('Vehicle Type Code') or ''
        xmlid = application_xmlid(ref, make_code, model, serie, vtc)
        if xmlid in seen:
            continue
        seen.add(xmlid)
        out.append({
            'id': xmlid,
            'product_tmpl_id/id': template_xmlid(make_code, ref),
            'make_id/id': make_xmlid(make_code),
            'model': model,
            'serie': serie,
            'vehicle_type_code': vtc,
        })
    return out


def build_image_manifest(image_rows):
    manifest = []
    for row in image_rows:
        ref = row.get('reference') or ''
        filename = row.get('filename') or ''
        if ref and filename:
            manifest.append({'reference': ref, 'filename': filename})
    return manifest


def build_prices_index(price_rows):
    idx = {}
    for row in price_rows:
        ref = row.get('Partno') or row.get('reference') or ''
        price = row.get('Prix') or row.get('price') or ''
        if ref and price:
            idx[ref] = to_float(price)
    return idx


# ---------- CSV writers ----------

def write_csv(path, rows, columns):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, '') for c in columns})


def main():
    ap = argparse.ArgumentParser(description='Convert TVH catalog files into Odoo-loadable CSVs.')
    ap.add_argument('--input-dir', required=True)
    ap.add_argument('--output-dir', required=True)
    args = ap.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = find_input_files(in_dir)
    print(f'Discovered inputs: {[k for k in files]}', file=sys.stderr)

    catalog_rows = read_catalog(files['catalog'])
    application_rows = read_pipe(files['applications']) if 'applications' in files else []
    image_rows = read_semicolon(files['images']) if 'images' in files else []
    price_rows = read_semicolon(files['prices']) if 'prices' in files else []
    prices_by_ref = build_prices_index(price_rows)

    # data.source is preloaded by the product_catalog addon (xmlid product_catalog.data_source_tvh).
    # The other CSVs reference it; no need to emit a data.source CSV.

    # 2. makes
    makes = build_makes(catalog_rows)
    write_csv(out_dir / '02_product_make.csv', list(makes.values()),
              ['id', 'code', 'name', 'data_source_id/id'])

    # 3. categories — written in depth order so parents always precede children
    categories = build_categories(catalog_rows)
    write_csv(out_dir / '03_product_public_category.csv', list(categories.values()),
              ['id', 'name', 'parent_id/id'])

    # 4. templates
    templates = build_templates(catalog_rows, prices_by_ref)
    write_csv(out_dir / '04_product_template.csv', templates,
              ['id', 'name', 'default_code', 'type', 'sale_ok', 'purchase_ok',
               'data_source_id/id', 'make_id/id', 'public_categ_ids/id',
               'is_dangerous_goods',
               'weight_gr', 'length_mm', 'width_mm', 'height_mm',
               'weight', 'list_price'])

    # 5. applications
    applications = build_applications(application_rows)
    write_csv(out_dir / '05_product_application.csv', applications,
              ['id', 'product_tmpl_id/id', 'make_id/id', 'model', 'serie', 'vehicle_type_code'])

    # 6. image manifest
    write_csv(out_dir / '06_image_manifest.csv', build_image_manifest(image_rows),
              ['reference', 'filename'])

    print(f'Wrote: data_source=1, makes={len(makes)}, categories={len(categories)}, '
          f'templates={len(templates)}, applications={len(applications)}', file=sys.stderr)


if __name__ == '__main__':
    main()
