from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    machine_serial = fields.Char('Machine Serial')
    part_number = fields.Char('Part Number')
    commentary = fields.Char('Commentary')

    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            line.machine_serial = line.product_id.product_tmpl_id.machine_serial
            line.part_number = line.product_id.product_tmpl_id.part_number
        return lines
