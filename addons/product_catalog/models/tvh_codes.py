from odoo import fields, models


class TvhAvailabilityCode(models.Model):
    _name = 'tvh.availability.code'
    _description = 'TVH availability code'
    _order = 'code'
    _rec_name = 'code'

    code = fields.Char('Code', required=True, index=True)
    description = fields.Char('Description')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Availability code must be unique.'),
    ]

    def _compute_display_name(self):
        for r in self:
            r.display_name = f'{r.code} — {r.description}' if r.description else r.code


class TvhUnitCode(models.Model):
    _name = 'tvh.unit.code'
    _description = 'TVH unit code'
    _order = 'code'
    _rec_name = 'code'

    code = fields.Char('Code', required=True, index=True)
    description = fields.Char('Description')
    iso_code = fields.Char('ISO code')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Unit code must be unique.'),
    ]

    def _compute_display_name(self):
        for r in self:
            r.display_name = f'{r.code} — {r.description}' if r.description else r.code


class ProductTvhQuantityDiscount(models.Model):
    _name = 'product.tvh.quantity.discount'
    _description = 'TVH quantity discount tier'
    _order = 'product_tmpl_id, qty'

    product_tmpl_id = fields.Many2one(
        'product.template', 'Product', required=True, ondelete='cascade', index=True)
    qty = fields.Float('From quantity', required=True)
    price = fields.Float('Unit price', required=True)
