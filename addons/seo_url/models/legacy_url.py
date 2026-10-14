import re
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools import file_open

KNOWN_URLS_FILE = 'seo_url/data/known_urls.txt'


def normalize_path(path):
    """Compare paths the way the frontend normalises urls before looking them
    up: leading slash, lowercase, no trailing slash."""
    path = (path or '').strip().lower()
    if not path.startswith('/'):
        path = '/' + path
    return path.rstrip('/') or '/'


def record_url(record):
    """The record's public path, or None. `website_slug` can be translated, so
    it may arrive as an {'en_US': ...} dict."""
    slug = record.with_context(lang='en_US').website_slug
    if isinstance(slug, dict):
        slug = slug.get('en_US') or next(iter(slug.values()), None)
    if not slug:
        return None
    return slug if slug.startswith('/') else f'/{slug}'


def is_live(record):
    if 'active' in record._fields and not record.active:
        return False
    if 'is_published' in record._fields and not record.is_published:
        return False
    return True


class LegacyUrl(models.Model):
    """An old public path that now belongs to a record. The frontend answers it
    with a 301 to the record's current url, so the target follows the record
    instead of being a stored url that can go stale."""
    _name = 'legacy.url'
    _description = 'Legacy URL (301 redirect)'
    _rec_name = 'path'
    _order = 'path'

    path = fields.Char(required=True, index=True)
    res_model = fields.Char('Target model', required=True)
    res_id = fields.Many2oneReference('Target record', model_field='res_model', required=True)

    _sql_constraints = [
        ('path_unique', 'unique(path)', 'This path already redirects to a record.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'path' in vals:
                vals['path'] = normalize_path(vals['path'])
        return super().create(vals_list)

    def write(self, vals):
        if 'path' in vals:
            vals['path'] = normalize_path(vals['path'])
        return super().write(vals)

    @api.model
    def add(self, paths, record):
        """Make each of `paths` redirect to `record`. An existing row is
        re-pointed: the newest owner of a path wins."""
        paths = {normalize_path(p) for p in paths if p}
        existing = self.sudo().search([('path', 'in', list(paths))])
        target = {'res_model': record._name, 'res_id': record.id}
        existing.write(target)
        self.sudo().create([dict(target, path=p) for p in paths - set(existing.mapped('path'))])

    @api.model
    def add_known_urls(self, prefix, model, id_map=None):
        """Redirect the known historical urls under `prefix` (data/known_urls.txt)
        to the record their trailing id belongs to now. The old storefront
        recomputed slugs on every rename, so many indexed urls exist in no
        database any more; their id is the only stable part. `id_map` maps old
        ids to new ones (None: the model kept its ids)."""
        records = self.env[model].sudo().with_context(active_test=False)
        added = 0
        with file_open(KNOWN_URLS_FILE) as known:
            for line in known:
                path = line.strip()
                match = re.search(r'-(\d+)$', path)
                if not path.startswith(prefix) or not match:
                    continue
                old_id = int(match.group(1))
                new_id = old_id if id_map is None else id_map.get(old_id)
                record = new_id and records.browse(new_id).exists()
                if record:
                    self.add([path], record)
                    added += 1
        return added

    @api.model
    def redirect_map(self):
        """{old path: current url} for every row whose record still has a live
        page. Rows pointing at deleted or unpublished records are left out, so
        those paths fall through to a 404."""
        rows_by_model = defaultdict(list)
        for row in self.sudo().search([]):
            rows_by_model[row.res_model].append(row)

        result = {}
        for model, rows in rows_by_model.items():
            if model not in self.env:
                continue
            records = self.env[model].sudo().with_context(active_test=False) \
                .browse([row.res_id for row in rows]).exists()
            urls = {rec.id: record_url(rec) for rec in records if is_live(rec)}
            for row in rows:
                url = urls.get(row.res_id)
                # A path that is the record's current url again is not a redirect.
                if url and normalize_path(url) != row.path:
                    result[row.path] = url
        return result
