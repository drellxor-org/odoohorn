from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.public.category'

    page_message = fields.Text('Page Message', translate=True)
