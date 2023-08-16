from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    order_line_ids = fields.One2many('sale.order.line', 'product_template_id', 'Order lines')
    popularity = fields.Integer('Popularity', compute='_compute_popularity', store=True)

    @api.depends('order_line_ids')
    def _compute_popularity(self):
        for template in self:
            template.popularity = len(template.order_line_ids)
