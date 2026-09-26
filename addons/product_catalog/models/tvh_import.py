"""Daily TVH import over FTPS.

TVH drops these files in the `silverhorn/` folder of their FTPS server:
    Silverhorn_TLH-catalog.csv               products, rarely changes
    Silverhorn_TLH-catalog-applications.csv  vehicles each part fits, rarely changes
    images_url_TLH_silverhorn.csv            main image URL per part
    Silverhorn_*pricefile*.xlsx              negotiated price per part
    stock_counts_<account>_<YYYYMMDD>.csv    stock, one file per day (only the newest matters)

Every step diffs the file against what is already stored in Odoo (row digest on
product.template / product.application, image URL, stock and price values), so only
changed rows are written and a failed or interrupted run heals on the next one.

Only the image step is slow (one download per image; TVH already overlays the
Silverhorn branding, so images are stored as delivered). It stops at the run's
deadline and re-triggers the cron to pick up where it left off.
"""

import base64
import csv
import ftplib
import hashlib
import io
import logging
import os
import re
import ssl
import tempfile
import time
import zipfile
from collections import defaultdict
from xml.etree import ElementTree

import requests

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_FTP_HOST = 'ftp02.irmn.com'
DEFAULT_FTP_FOLDER = 'silverhorn'

# TVH column suffix → Odoo language code. en is the source value; the rest are translations.
LANGS = {'en': 'en_US', 'fr': 'fr_FR', 'es': 'es_ES', 'nl': 'nl_NL', 'it': 'it_IT', 'de': 'de_DE'}
CATEGORY_LEVELS = ('family', 'subfamily', 'sub_subfamily')

STOCK_RE = re.compile(r'^stock_counts_\d+_(\d{8})\.csv$')
STEPS = ('catalog', 'applications', 'prices', 'stock', 'images')

# Stay well inside limit_time_real_cron (3600s); the image step re-triggers the cron.
RUN_BUDGET_SECONDS = 40 * 60
IMAGE_COMMIT_EVERY = 100

# ftp02.irmn.com sends only its leaf certificate, without the GoDaddy G2 intermediate, so
# verification against the system store fails. Supply the (public) intermediate ourselves;
# the chain is still verified up to the system's GoDaddy root. Valid until 2031-05-03.
FTP_EXTRA_CA = os.path.join(os.path.dirname(__file__), '..', 'certs', 'godaddy_g2_intermediate.pem')

XLSX_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


class _FTP_TLS(ftplib.FTP_TLS):
    """FTP_TLS that reuses the control channel's TLS session on data connections.

    Most FTPS servers require it ("522 session reuse required"); stdlib doesn't do it.
    """

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(
                conn, server_hostname=self.host, session=self.sock.session)
        return conn, size


# ---------------------------------------------------------------------------
#   Pure helpers
# ---------------------------------------------------------------------------

def pick_files(names):
    """Map step → file name from a folder listing. Newest stock file wins."""
    picked, stock, prices = {}, [], []
    for name in map(os.path.basename, names):
        low = name.lower()
        if low.endswith('_tlh-catalog.csv'):
            picked['catalog'] = name
        elif low.endswith('_tlh-catalog-applications.csv'):
            picked['applications'] = name
        elif low.startswith('images_url_') and low.endswith('.csv'):
            picked['images'] = name
        elif 'pricefile' in low and low.endswith('.xlsx'):
            prices.append(name)
        elif STOCK_RE.match(low):
            stock.append((STOCK_RE.match(low).group(1), name))
    if stock:
        picked['stock'] = max(stock)[1]
    if prices:
        # ponytail: newest by name; TVH only ships the "initial" file so far. Switch to MDTM
        # if they start publishing dated price files.
        picked['prices'] = max(prices)
    return picked


def read_csv(path):
    """DictReader over a TVH csv; delimiter sniffed from the header (TVH mixes , ; |)."""
    with open(path, encoding='utf-8-sig', newline='') as f:
        text = f.read()
    header = text.split('\n', 1)[0]
    return csv.DictReader(io.StringIO(text), delimiter=max(',;|', key=header.count))


def read_xlsx(path):
    """Rows of the first sheet as dicts keyed by the header row. Stdlib only."""
    with zipfile.ZipFile(path) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            for si in ElementTree.fromstring(z.read('xl/sharedStrings.xml')):
                # plain <t>, or rich-text runs <r><t>; skips phonetic <rPh> hints
                runs = si.findall(XLSX_NS + 't') + si.findall(XLSX_NS + 'r/' + XLSX_NS + 't')
                shared.append(''.join(t.text or '' for t in runs))
        sheet = ElementTree.fromstring(z.read('xl/worksheets/sheet1.xml'))
    header = None
    for row in sheet.iter(XLSX_NS + 'row'):
        cells = {}
        for c in row.iter(XLSX_NS + 'c'):
            col = re.match(r'[A-Z]+', c.get('r')).group()
            v = c.find(XLSX_NS + 'v')
            if c.get('t') == 's':
                cells[col] = shared[int(v.text)]
            elif c.get('t') == 'inlineStr':
                cells[col] = ''.join(t.text or '' for t in c.iter(XLSX_NS + 't'))
            else:
                cells[col] = v.text if v is not None else ''
        if header is None:
            header = cells
            continue
        yield {header[col]: val.strip() for col, val in cells.items() if col in header}


def digest(row):
    return hashlib.sha1('\x1f'.join((v or '').strip() for v in row.values()).encode()).hexdigest()


def to_float(value):
    try:
        return float((value or '').strip().replace(',', '.'))
    except ValueError:
        return 0.0


def to_stock(value):
    """TVH Stockfile convention the storefront expects: 'NO', '1'..'10', '+10'."""
    value = (value or '').strip()
    return value if value.startswith('+') or (value.isdigit() and int(value) > 0) else 'NO'


def _match_brochure(haystack, candidates):
    """The single most specific brochure whose name tokens all appear in haystack."""
    best, best_size = [], 0
    for bid, toks in candidates:
        if toks <= haystack:
            if len(toks) > best_size:
                best, best_size = [bid], len(toks)
            elif len(toks) == best_size:
                best.append(bid)
    return best[0] if len(best) == 1 else False


def _tokens(s):
    return set(re.findall(r'[a-z0-9]+', (s or '').lower()))


# ---------------------------------------------------------------------------
#   Importer
# ---------------------------------------------------------------------------

class TvhImport(models.AbstractModel):
    _name = 'tvh.import'
    _description = 'TVH FTPS import'

    @api.model
    def cron_import(self):
        with tempfile.TemporaryDirectory(prefix='tvh-') as workdir:
            self._download(workdir)
            self.import_dir(workdir)

    @api.model
    def import_dir(self, path):
        """Run every step on the files found in `path`. Each step commits on its own."""
        deadline = time.monotonic() + RUN_BUDGET_SECONDS
        files = pick_files(os.listdir(path))
        for step in STEPS:
            if step not in files:
                _logger.warning('[tvh import] no %s file found, skipping', step)
                continue
            _logger.info('[tvh import] %s <- %s', step, files[step])
            try:
                args = (deadline,) if step == 'images' else ()
                getattr(self, '_import_' + step)(os.path.join(path, files[step]), *args)
                self.env.cr.commit()
            except Exception:
                self.env.cr.rollback()
                _logger.exception('[tvh import] %s failed', step)

    # ------------------------------------------------------------------------
    #   FTPS
    # ------------------------------------------------------------------------

    @api.model
    def _download(self, workdir):
        param = self.env['ir.config_parameter'].sudo()
        host = param.get_param('tvh.ftp.host') or DEFAULT_FTP_HOST
        user = param.get_param('tvh.ftp.user')
        password = param.get_param('tvh.ftp.password')
        folder = param.get_param('tvh.ftp.folder') or DEFAULT_FTP_FOLDER
        if not (user and password):
            raise UserError(_('TVH FTPS credentials are not configured (Settings → TVH API).'))
        context = ssl.create_default_context()
        context.load_verify_locations(cafile=FTP_EXTRA_CA)
        with _FTP_TLS(host, context=context, timeout=120) as ftp:
            ftp.login(user, password)
            ftp.prot_p()
            ftp.cwd(folder)
            for name in pick_files(ftp.nlst()).values():
                with open(os.path.join(workdir, name), 'wb') as f:
                    ftp.retrbinary('RETR ' + name, f.write)

    # ------------------------------------------------------------------------
    #   Lookups
    # ------------------------------------------------------------------------

    def _products(self, *columns):
        """{(make code, reference): (id, *columns)} for every product with a make,
        archived included. `columns` are product_template column names (constants)."""
        cols = ''.join(', t.' + c for c in columns)
        self.env.flush_all()  # default_code is a stored compute, written on flush
        self.env.cr.execute(
            'SELECT m.code, t.default_code, t.id' + cols +
            ' FROM product_template t JOIN product_make m ON m.id = t.make_id')
        return {(row[0], row[1]): row[2:] for row in self.env.cr.fetchall()}

    def _makes(self, names=None):
        """{code: product.make id} for TVH makes, creating/naming the ones in `names`."""
        source = self.env.ref('product_catalog.data_source_tvh')
        Make = self.env['product.make'].sudo()
        makes = {m.code: m for m in Make.search([('data_source_id', '=', source.id)])}
        for code, name in (names or {}).items():
            if code not in makes:
                makes[code] = Make.create({'code': code, 'name': name or code,
                                           'data_source_id': source.id})
            elif name and makes[code].name == code:
                # stub created by an inquiry before the catalog knew the make
                makes[code].name = name
        return {code: m.id for code, m in makes.items()}

    # ------------------------------------------------------------------------
    #   Steps
    # ------------------------------------------------------------------------

    def _import_catalog(self, path):
        rows = list(read_csv(path))
        products = self._products('tvh_source_digest')
        changed = [r for r in rows
                   if products.get((r['make'], r['reference']), (None, None))[1] != digest(r)]
        if changed:
            for code in LANGS.values():
                self.env['res.lang']._activate_lang(code)

        makes = self._makes({r['make']: r['make_description'].strip() for r in changed})
        categories = self._category_cache()
        Tmpl = self.env['product.template'].sudo().with_context(lang='en_US')
        source = self.env.ref('product_catalog.data_source_tvh')

        created = updated = 0
        new_vals, new_rows = [], []
        for r in changed:
            weight_gr = to_float(r['weight_gr'])
            categ_id = self._category(r, categories)
            vals = {
                'name': r['description_en'].strip() or r['reference'],
                'default_code': r['reference'],
                'make_id': makes[r['make']],
                'is_dangerous_goods': r['dangerous_goods'].strip().upper() == 'TRUE',
                'weight_gr': weight_gr,
                'length_mm': to_float(r['length_mm']),
                'width_mm': to_float(r['width_mm']),
                'height_mm': to_float(r['height_mm']),
                'weight': weight_gr / 1000.0,
                'public_categ_ids': [(6, 0, [categ_id] if categ_id else [])],
                'tvh_source_digest': digest(r),
                'active': True,
            }
            existing = products.get((r['make'], r['reference']))
            if existing:
                tmpl = Tmpl.browse(existing[0])
                tmpl.write(vals)
                self._translate(tmpl, 'name', r, 'description')
                updated += 1
            else:
                new_vals.append(dict(vals, type='product', sale_ok=True, purchase_ok=True,
                                     data_source_id=source.id))
                new_rows.append(r)
        for i in range(0, len(new_vals), 500):
            for tmpl, r in zip(Tmpl.create(new_vals[i:i + 500]), new_rows[i:i + 500]):
                self._translate(tmpl, 'name', r, 'description')
                created += 1

        # Archive catalog products TVH dropped. Products without a digest (inquiry stubs
        # for alternatives/replacements) were never in the catalog, so leave them alone.
        in_file = {(r['make'], r['reference']) for r in rows}
        gone = [v[0] for k, v in products.items() if k not in in_file and v[1]]
        archived = Tmpl.browse(gone).filtered('active')
        archived.write({'active': False})
        _logger.info('[tvh import] catalog: %s created, %s updated, %s archived',
                     created, updated, len(archived))

    def _category_cache(self):
        Cat = self.env['product.public.category'].sudo().with_context(lang='en_US')
        return {(c.parent_id.id, c.name): c.id for c in Cat.search([])}

    def _category(self, row, cache):
        """Deepest public category of the row, creating the path on the way."""
        Cat = self.env['product.public.category'].sudo().with_context(lang='en_US')
        parent_id = False
        for level in CATEGORY_LEVELS:
            name = (row.get(level + '_en') or '').strip()
            if not name:
                break
            key = (parent_id, name)
            if key not in cache:
                cat = Cat.create({'name': name, 'parent_id': parent_id})
                # ponytail: translations come from the first row that creates the node; TVH's
                # per-language trees don't always line up with the English one.
                self._translate(cat, 'name', row, level)
                cache[key] = cat.id
            parent_id = cache[key]
        return parent_id

    def _translate(self, record, field, row, prefix):
        translations = {code: row[prefix + '_' + lang].strip()
                        for lang, code in LANGS.items()
                        if lang != 'en' and (row.get(prefix + '_' + lang) or '').strip()}
        if translations:
            record.update_field_translations(field, translations)

    def _import_applications(self, path):
        App = self.env['product.application'].sudo()
        cr = self.env.cr
        products = self._products()
        makes = self._makes()

        self.env.flush_all()
        cr.execute('SELECT id, source_key, product_tmpl_id, model, serie, brochure_id'
                   ' FROM product_application')
        existing, legacy = {}, []
        for row in cr.fetchall():
            if row[1]:
                existing[row[1]] = row
            else:
                legacy.append(row)  # rows from the pre-cron import script

        seen, new, unknown = set(), {}, 0
        for r in read_csv(path):
            key = digest(r)
            seen.add(key)
            if key in existing or key in new:
                continue
            product = products.get((r['Make'], r['Reference']))
            if not product:
                unknown += 1
                continue
            new[key] = {
                'source_key': key,
                'product_tmpl_id': product[0],
                'make_id': makes.get(r['Make'], False),
                'vehicle_type_code': r['Vehicle_Type_Code'].strip(),
                'vehicle_brand': r['Vehicle_Brand'].strip(),
                'model': r['model'].strip(),
                'serie': r['serie'].strip(),
                'engine_brand': r['Engine_Brand'].strip(),
                'engine_series': r['Engine_Series'].strip(),
                'engine_model': r['Engine_Model'].strip(),
            }

        stale = [row for key, row in existing.items() if key not in seen] + legacy
        # Brochure links are partly hand-made; keep them when a vehicle row is replaced.
        brochures = {(row[2], row[3] or '', row[4] or ''): row[5] for row in stale if row[5]}
        for vals in new.values():
            vals['brochure_id'] = brochures.get(
                (vals['product_tmpl_id'], vals['model'], vals['serie']), False)

        stale_ids = [row[0] for row in stale]
        for i in range(0, len(stale_ids), 10000):
            App.browse(stale_ids[i:i + 10000]).unlink()
        new_vals = list(new.values())
        unlinked = []
        for i in range(0, len(new_vals), 5000):
            chunk = new_vals[i:i + 5000]
            for app, vals in zip(App.create(chunk), chunk):
                if not vals['brochure_id']:
                    unlinked.append((app.id, vals['vehicle_brand'], vals['model'], vals['serie']))
        linked = self._match_brochures(unlinked)
        _logger.info('[tvh import] applications: %s created, %s removed, %s brochures matched, '
                     '%s rows for unknown products', len(new_vals), len(stale_ids), linked, unknown)

    def _match_brochures(self, apps, min_tokens=2):
        """Link applications to the one brochure whose name tokens all appear in
        vehicle brand + model + serie. Ambiguous and zero matches are left for manual work.
        `apps` is a list of (id, vehicle_brand, model, serie)."""
        if not apps:
            return 0
        candidates = [(b.id, toks) for b in self.env['brochure'].sudo().search([])
                      for toks in [_tokens(b.name)] if len(toks) >= min_tokens]
        by_haystack = defaultdict(list)
        for app_id, *parts in apps:
            by_haystack[tuple(parts)].append(app_id)
        by_brochure = defaultdict(list)
        for parts, ids in by_haystack.items():
            bid = _match_brochure(_tokens(' '.join(filter(None, parts))), candidates)
            if bid:
                by_brochure[bid] += ids
        App = self.env['product.application'].sudo()
        for bid, ids in by_brochure.items():
            App.browse(ids).write({'brochure_id': bid})
        return sum(len(ids) for ids in by_brochure.values())

    def _import_prices(self, path):
        """Apply the price file to tvh_price only where the file's own value changed, so a
        manual "Refresh from TVH" (newer, live price) survives re-reading the same file.

        list_price (shop price) is kept at tvh_price, falling back to the file price; the
        markup is applied by Odoo pricelists."""
        products = self._products('tvh_pricefile_price', 'tvh_price', 'list_price')
        Tmpl = self.env['product.template'].sudo()
        updated = 0
        for r in read_xlsx(path):
            price_col = next((k for k in r if k.lower().startswith('sales price')), None)
            product = products.get((r.get('Make'), r.get('Partno')))
            if not (price_col and product and r[price_col]):
                continue
            product_id, file_price, tvh_price, list_price = product
            price = round(to_float(r[price_col]), 2)
            vals = {}
            if file_price != price:
                vals = {'tvh_price': price, 'tvh_pricefile_price': price}
                tvh_price = price
            # list_price is a numeric column (Decimal from SQL); compare as rounded floats
            if round(float(list_price or 0), 2) != round(tvh_price or price, 2):
                vals['list_price'] = tvh_price or price
            if vals:
                Tmpl.browse(product_id).write(vals)
                updated += 1
        _logger.info('[tvh import] prices: %s updated', updated)

    def _import_stock(self, path):
        products = self._products('tvh_quantity_in_stock', 'tvh_quantity_in_stock_be')
        by_value = defaultdict(list)
        for r in read_csv(path):
            product = products.get((r['make'], r['reference']))
            value = (to_stock(r['stock_UK']), to_stock(r['stock_BE']))
            if product and product[1:] != value:
                by_value[value].append(product[0])
        Tmpl = self.env['product.template'].sudo()
        for (uk, be), ids in by_value.items():
            Tmpl.browse(ids).write({'tvh_quantity_in_stock': uk, 'tvh_quantity_in_stock_be': be})
        _logger.info('[tvh import] stock: %s updated', sum(map(len, by_value.values())))

    def _import_images(self, path, deadline):
        products = self._products('tvh_image_url')
        todo = []
        for r in read_csv(path):
            product = products.get((r['Make'], r['PartNumber']))
            url = (r['main_image_URL'] or '').strip()
            # Compare without the query: it only carries lang + an account-wide extrakey,
            # and a rotated key must not re-download every image.
            if product and url and (product[1] or '').split('?')[0] != url.split('?')[0]:
                todo.append((product[0], url))

        Tmpl = self.env['product.template'].sudo()
        session = requests.Session()
        # TVH's image CDN answers 403 to the default python-requests User-Agent.
        session.headers['User-Agent'] = 'Silverhorn-Odoo/1.0'
        done = failed = 0
        for product_id, url in todo:
            if time.monotonic() > deadline:
                _logger.info('[tvh import] images: out of time, %s left, re-triggering',
                             len(todo) - done - failed)
                self.env.ref('product_catalog.cron_tvh_import')._trigger()
                break
            try:
                resp = session.get(url, timeout=30)
                resp.raise_for_status()
                with self.env.cr.savepoint():  # Odoo rejects non-image bytes here
                    Tmpl.browse(product_id).write({'image_1920': base64.b64encode(resp.content),
                                                   'tvh_image_url': url})
            except Exception as e:
                # Leave tvh_image_url untouched so tomorrow's run retries it.
                _logger.warning('[tvh import] image for product %s failed: %s', product_id, e)
                failed += 1
                continue
            done += 1
            if done % IMAGE_COMMIT_EVERY == 0:
                self.env.cr.commit()
        _logger.info('[tvh import] images: %s written, %s failed', done, failed)
