from odoo import fields, models


class ProductApplication(models.Model):
    _name = 'product.application'
    _description = 'Product application (vehicle the part fits)'
    _order = 'product_tmpl_id, make_id, model, serie'

    product_tmpl_id = fields.Many2one(
        'product.template', 'Product', required=True, ondelete='cascade', index=True)
    make_id = fields.Many2one('product.make', 'Make', index=True)
    model = fields.Char('Model')
    serie = fields.Char('Serie')
    vehicle_type_code = fields.Char('Vehicle type code')
    vehicle_brand = fields.Char('Vehicle brand')
    engine_brand = fields.Char('Engine brand')
    engine_series = fields.Char('Engine series')
    engine_model = fields.Char('Engine model')
    source_key = fields.Char('Source key', index=True, copy=False, readonly=True,
                             help='Digest of the TVH applications row this record was imported from.')
    brochure_id = fields.Many2one('brochure', 'Brochure', ondelete='set null',
                                  help='Optional link to a brochure (parts diagram) for this vehicle.')
