from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    machine_serial = fields.Char('Machine Serial')
    part_number = fields.Char('Part Number')
    commentary = fields.Char('Commentary')
