from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slugify


class BrochureCategory(models.Model):
    _name = 'brochure.category'
    _description = 'Brochure Category'
    _inherit = ['image.mixin', 'website.seo.metadata', 'website.published.mixin']
    _parent_name = 'parent_id'
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'sequence, name'

    name = fields.Char('Name', required=True, translate=True)
    complete_name = fields.Char('Full Name', compute='_compute_complete_name', recursive=True, store=True)
    sequence = fields.Integer('Sequence', default=10)
    parent_id = fields.Many2one('brochure.category', 'Parent', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    child_id = fields.One2many('brochure.category', 'parent_id', 'Children')

    page_message = fields.Text('Page Message', translate=True)

    website_slug = fields.Char('Website Slug', compute='_compute_website_slug', store=True, readonly=True,
                               translate=True)
    website_slug_override = fields.Char('User-defined website slug')
    json_ld = fields.Char('JSON-LD')

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for cat in self:
            if cat.parent_id:
                cat.complete_name = f'{cat.parent_id.complete_name} / {cat.name}'
            else:
                cat.complete_name = cat.name

    @api.depends('name', 'website_slug_override', 'parent_id.website_slug')
    def _compute_website_slug(self):
        prefix = '/brochure-category'
        for cat in self:
            if cat.website_slug_override:
                cat.website_slug = cat.website_slug_override
                continue
            slug_list = cat._slugify_category()
            cat.website_slug = f'{prefix}/{"/".join(slug_list)}' if slug_list else False

    def _slugify_category(self):
        slug_list = []
        node = self
        while node:
            slug_list.insert(0, slugify(f'{node.name or ""}-{node.id}').strip().strip('-'))
            node = node.parent_id
        return slug_list

    def _default_is_published(self):
        return True
