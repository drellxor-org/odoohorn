from odoo import fields, models


class ProductMake(models.Model):
    _name = 'product.make'
    _description = 'Product make / manufacturer'
    _order = 'name'
    _rec_name = 'name'

    code = fields.Char('Code', required=True, index=True)
    name = fields.Char('Name', required=True)
    data_source_id = fields.Many2one('data.source', 'Data source', ondelete='restrict')

    _sql_constraints = [
        ('code_source_unique',
         'unique(code, data_source_id)',
         'Make code must be unique per data source.'),
    ]
