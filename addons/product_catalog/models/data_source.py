from odoo import fields, models


class DataSource(models.Model):
    _name = 'data.source'
    _description = 'External data source'
    _order = 'name'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Data source code must be unique.'),
    ]
