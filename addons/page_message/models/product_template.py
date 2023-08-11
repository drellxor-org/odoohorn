from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    page_message = fields.Text('Page Message')
