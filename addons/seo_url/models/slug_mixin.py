from psycopg2.extras import execute_values

from odoo import api, models
from odoo.addons.http_routing.models.ir_http import slugify as _slugify


def slugify(text):
    return _slugify(text or '').strip().strip('-')


def _slug_column(model):
    """Products, brochures and categories keep a translated (jsonb) column with
    the slug under en_US only; articles a plain one. Both stay as they are:
    search_corpus reads them, and converting a translated column in Odoo 16
    drops that view."""
    return "website_slug->>'en_US'" if model._fields['website_slug'].translate else 'website_slug'


def ensure_slug_index(model):
    """One record per public url."""
    model.env.cr.execute(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {model._table}_website_slug_uniq
            ON {model._table} (({_slug_column(model)}))
         WHERE website_slug IS NOT NULL
    """)


def taken_slugs(model, exclude_ids=()):
    model.env.cr.execute(
        f"SELECT {_slug_column(model)} FROM {model._table} "
        f"WHERE website_slug IS NOT NULL AND NOT (id = ANY(%s))",
        [list(exclude_ids)])
    return {row[0] for row in model.env.cr.fetchall() if row[0]}


def write_slugs(model, slug_by_id):
    """Bulk write in SQL: a catalog-wide migration through the ORM would fire
    every write() override (cache invalidation, search marks) 13k times. The
    search_corpus view is rebuilt by graphql_vuestorefront's update anyway."""
    if not slug_by_id:
        return
    value = "jsonb_build_object('en_US', v.slug)" if model._fields['website_slug'].translate else 'v.slug'
    # Clear first: a new slug may equal another rewritten record's old one, and
    # the unique index is checked row by row within the UPDATE.
    model.env.cr.execute(f'UPDATE {model._table} SET website_slug = NULL WHERE id = ANY(%s)',
                         [list(slug_by_id)])
    execute_values(model.env.cr, f"""
        UPDATE {model._table} t SET website_slug = {value}
          FROM (VALUES %s) AS v(id, slug)
         WHERE t.id = v.id
    """, list(slug_by_id.items()))
    model.browse(list(slug_by_id)).invalidate_recordset(['website_slug'])


class SeoSlugMixin(models.AbstractModel):
    """A permanent public url. The slug is assigned once, when the record is
    created, and does not follow renames: a url that reached Google must keep
    working. Models list their candidates in order of preference
    (_slug_candidates); the first one no other record uses wins, then the
    first candidate with -2, -3…

    Concrete models declare `website_slug` themselves (copy=False), see
    _slug_column for why the column types differ."""
    _name = 'seo.slug.mixin'
    _description = 'Permanent website slug'

    def _slug_candidates(self):
        """Readable slugs for this record, best first. Must not be empty."""
        raise NotImplementedError

    def init(self):
        super().init()
        if not self._abstract:
            ensure_slug_index(self)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(lambda r: not r.website_slug)._assign_slugs()
        return records

    def _assign_slugs(self):
        """Give each record in self a slug, ignoring what it has now. Only for
        records whose url is not public yet: creation and one-off migrations."""
        if not self:
            return
        taken = taken_slugs(self, self.ids)
        slugs = {}
        for record in self.sorted('id').with_context(lang='en_US'):
            candidates = record._slug_candidates()
            slug = next((c for c in candidates if c not in taken), None)
            n = 1
            while slug is None or slug in taken:
                n += 1
                slug = f'{candidates[0]}-{n}'
            taken.add(slug)
            slugs[record.id] = slug
        write_slugs(self, slugs)
