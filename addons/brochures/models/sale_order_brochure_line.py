from odoo import fields, models


class SaleOrderBrochureLine(models.Model):
    _name = 'sale.order.brochure.line'
    _description = 'Sale order brochure line'
    _order = 'order_id, sequence, id'

    order_id = fields.Many2one('sale.order', 'Order', required=True, ondelete='cascade', index=True)
    brochure_id = fields.Many2one('brochure', 'Brochure', required=True, ondelete='restrict')
    name = fields.Char('Description')
    sequence = fields.Integer('Sequence', default=10)

    machine_serial = fields.Char('Machine Serial')
    part_number = fields.Char('Part Number')
    commentary = fields.Char('Commentary')
