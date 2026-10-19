from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    brochure_line_ids = fields.One2many('sale.order.brochure.line', 'order_id', 'Brochure lines')
