from odoo import fields, models


class ArticleImage(models.Model):
    _name = 'article.image'
    _description = 'Article Images'
    _inherit = ['image.mixin']
    _order = "sequence"

    article_id = fields.Many2one('article', 'Article', required=True, ondelete='cascade')
    image_64 = fields.Image("Image 64", related="image_1920", max_width=64, max_height=64, store=True)
    sequence = fields.Integer('Sequence')
