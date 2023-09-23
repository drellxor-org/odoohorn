from odoo import fields, models


class Article(models.Model):
    _name = 'article'
    _inherit = ['article', 'website.seo.metadata']
