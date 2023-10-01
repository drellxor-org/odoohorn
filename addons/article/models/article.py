from odoo import fields, models
from odoo.addons.http_routing.models.ir_http import slugify


class Article(models.Model):
    _name = 'article'
    _description = 'Articles'
    _inherit = ['image.mixin', 'website.published.mixin']
    _order = "sequence, name"

    name = fields.Char('Title', required=True, translate=True)
    body = fields.Text('Body', required=True, translate=True)
    sequence = fields.Integer('Sequence')

    image_32 = fields.Image("Image 32", related="image_1920", max_width=32, max_height=32, store=True)

    website_slug = fields.Char('Website slug', readonly=True, compute='_compute_website_slug', store=True)

    def _default_is_published(self):
        return True

    def _compute_website_slug(self):
        for article in self:
            prefix = '/article'
            slug_name = slugify(article.name or '').strip().strip('-')
            article.website_slug = f'{prefix}/{slug_name}-{article.id}'
