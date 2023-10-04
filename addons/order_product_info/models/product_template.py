from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    order_line_ids = fields.One2many('sale.order.line', 'product_template_id', 'Order lines')
    popularity = fields.Integer('Popularity', compute='_compute_popularity', store=True)

    machine_serial = fields.Char('Machine Serial')
    part_number = fields.Char('Part Number')
    parent_template = fields.Many2one('product.template', 'Parent template')

    @api.depends('order_line_ids')
    def _compute_popularity(self):
        for template in self:
            template.popularity = len(template.order_line_ids)