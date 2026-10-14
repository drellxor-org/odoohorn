from odoo import api, fields, models
from odoo.addons.seo_url.models.slug_mixin import slugify


class Brochure(models.Model):
    _name = 'brochure'
    _description = 'Brochure'
    _inherit = ['website.seo.metadata', 'website.published.mixin', 'seo.slug.mixin']
    _order = 'sequence, name'

    name = fields.Char('Name', required=True, translate=True)
    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer('Sequence', default=10)

    page_message = fields.Text('Page Message', translate=True)
    description_sale = fields.Text('Sales Description', translate=True)

    category_ids = fields.Many2many('brochure.category', 'brochure_brochure_category_rel',
                                    'brochure_id', 'category_id', 'Categories')
    # One category owns the brochure's breadcrumb trail; the others only list it.
    # Also tells same-named models apart in their urls (see _slug_candidates).
    primary_category_id = fields.Many2one(
        'brochure.category', 'Primary category', compute='_compute_primary_category_id',
        store=True, readonly=False, domain="[('id', 'in', category_ids)]")
    category_slug_ids = fields.Many2many('brochure.category', 'brochure_brochure_category_slug_rel',
                                         'brochure_id', 'category_id',
                                         compute='_compute_category_slug_ids', store=True, readonly=True)

    attachment_ids = fields.One2many('brochure.attachment', 'brochure_id', 'Attachments')
    brochure_line_ids = fields.One2many('sale.order.brochure.line', 'brochure_id', 'Order brochure lines')
    popularity = fields.Integer('Popularity', compute='_compute_popularity', store=True)

    # Assigned once at creation by seo.slug.mixin; renames never change it.
    website_slug = fields.Char('Website Slug', readonly=True, translate=True, copy=False)
    json_ld = fields.Char('JSON-LD')

    @api.depends('brochure_line_ids')
    def _compute_popularity(self):
        for b in self:
            b.popularity = len(b.brochure_line_ids)

    def _slug_candidates(self):
        # /model/{name}: the name already starts with the make. Same-named models
        # (e.g. an "Early Models" and an "Excavators" copy) fall back to the
        # primary category's name, then to -2, -3…
        base = f'/model/{slugify(self.name) or self.id}'
        candidates = [base]
        if self.primary_category_id:
            candidates.append(f'{base}-{slugify(self.primary_category_id.name)}')
        return candidates

    @api.depends('category_ids')
    def _compute_primary_category_id(self):
        for b in self:
            if b.primary_category_id not in b.category_ids or not b.primary_category_id:
                b.primary_category_id = b._pick_primary_category()
            else:
                b.primary_category_id = b.primary_category_id

    def _pick_primary_category(self):
        """The category under the make the name starts with (a Yanmar engine
        also listed under Denyo belongs to Yanmar), deepest first."""
        name = (self.with_context(lang='en_US').name or '').lower()

        def rank(cat):
            make = (cat.complete_name or '').split(' / ')[0].lower()
            return (not name.startswith(make), -len(cat.parent_path or ''), cat.id)

        return min(self.category_ids, key=rank, default=self.env['brochure.category'])

    @api.model
    def _init_slugs(self):
        """Move urls to the final scheme (/catalog/…, /model/…). The older
        /brochure… formats were never public on prod, so no redirects. Runs on
        every update (data/slugs.xml), a no-op once done."""
        Category = self.env['brochure.category'].with_context(active_test=False)
        Category.search([], order='parent_path')._compute_website_slug()
        stale = self.with_context(active_test=False).search([]).filtered(
            lambda b: not (b.with_context(lang='en_US').website_slug or '').startswith('/model/'))
        stale._assign_slugs()

    @api.depends('category_ids', 'category_ids.parent_id')
    def _compute_category_slug_ids(self):
        for b in self:
            cat_ids = set()
            for cat in b.category_ids:
                node = cat
                while node:
                    cat_ids.add(node.id)
                    node = node.parent_id
            b.category_slug_ids = [(6, 0, list(cat_ids))]

    def _default_is_published(self):
        return True
