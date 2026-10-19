from odoo import models


class Article(models.Model):
    _name = 'article'
    _inherit = ['article', 'website.seo.metadata']
