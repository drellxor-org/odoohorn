from odoo import fields, models


class Article(models.Model):
    _name = 'article'
    _description = 'Articles'
    _inherit = ['image.mixin']
    _order = "sequence, name"

    name = fields.Char('Title', required=True, translate=True)
    body = fields.Text('Body', required=True, translate=True)
    sequence = fields.Integer('Sequence')

    image_32 = fields.Image("Image 32", related="image_1920", max_width=32, max_height=32, store=True)
