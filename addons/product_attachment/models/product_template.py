from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_attachment_ids = fields.One2many('product.attachment', 'product_id', 'Product Attachments')
