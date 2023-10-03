from odoo import fields, models, api
from odoo.addons.http_routing.models.ir_http import slugify


class Article(models.Model):
    _name = 'article'
    _description = 'Articles'
    _inherit = ['website.published.mixin']
    _order = "sequence, name"

    name = fields.Char('Title', required=True, translate=True)
    body = fields.Text('Body', required=True, translate=True)
    sequence = fields.Integer('Sequence')

    image_64 = fields.Image("Image 64", store=True, compute='_compute_image_1920')

    website_slug = fields.Char('Website slug', readonly=True, compute='_compute_website_slug', store=True)
    article_images = fields.One2many('article.image', 'article_id', 'Article images')

    def _default_is_published(self):
        return True

    def _compute_website_slug(self):
        for article in self:
            prefix = '/article'
            slug_name = slugify(article.name or '').strip().strip('-')
            article.website_slug = f'{prefix}/{slug_name}-{article.id}'

    @api.depends('article_images.sequence')
    def _compute_image_1920(self):
        for article in self:
            if article.article_images:
                top_image = min(article.article_images, key=lambda x: x.sequence)
                if top_image:
                    article.image_64 = top_image.image_64
            else:
                article.image_64 = False
