from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    data_source_id = fields.Many2one('data.source', 'Data source', ondelete='restrict')
    make_id = fields.Many2one('product.make', 'Make', ondelete='restrict', index=True)

    is_dangerous_goods = fields.Boolean('Dangerous goods')

    # Catalog values preserved in their original units.
    weight_gr = fields.Float('Packaged weight (g)')
    length_mm = fields.Float('Packaged length (mm)')
    width_mm = fields.Float('Packaged width (mm)')
    height_mm = fields.Float('Packaged height (mm)')

    application_ids = fields.One2many(
        'product.application', 'product_tmpl_id', 'Applications')
