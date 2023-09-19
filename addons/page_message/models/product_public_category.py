from odoo import fields, models


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    page_message = fields.Text('Page Message', translate=True)
