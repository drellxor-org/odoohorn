from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slugify


class Brochure(models.Model):
    _name = 'brochure'
    _description = 'Brochure'
    _inherit = ['website.seo.metadata', 'website.published.mixin']
    _order = 'sequence, name'

    name = fields.Char('Name', required=True, translate=True)
    active = fields.Boolean('Active', default=True)
    sequence = fields.Integer('Sequence', default=10)

    page_message = fields.Text('Page Message', translate=True)
    description_sale = fields.Text('Sales Description', translate=True)

    category_ids = fields.Many2many('brochure.category', 'brochure_brochure_category_rel',
                                    'brochure_id', 'category_id', 'Categories')
    category_slug_ids = fields.Many2many('brochure.category', 'brochure_brochure_category_slug_rel',
                                         'brochure_id', 'category_id',
                                         compute='_compute_category_slug_ids', store=True, readonly=True)

    attachment_ids = fields.One2many('brochure.attachment', 'brochure_id', 'Attachments')
    brochure_line_ids = fields.One2many('sale.order.brochure.line', 'brochure_id', 'Order brochure lines')
    popularity = fields.Integer('Popularity', compute='_compute_popularity', store=True)

    website_slug = fields.Char('Website Slug', compute='_compute_website_slug', store=True, readonly=True,
                               translate=True)
    website_slug_override = fields.Char('User-defined website slug')
    json_ld = fields.Char('JSON-LD')

    @api.depends('brochure_line_ids')
    def _compute_popularity(self):
        for b in self:
            b.popularity = len(b.brochure_line_ids)

    @api.depends('name', 'website_slug_override')
    def _compute_website_slug(self):
        prefix = '/brochure'
        for b in self:
            if b.website_slug_override:
                b.website_slug = b.website_slug_override
            elif not b.id:
                b.website_slug = False
            else:
                slug_name = slugify(b.name or '').strip().strip('-')
                b.website_slug = f'{prefix}/{slug_name}-{b.id}'

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
