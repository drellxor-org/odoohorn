from odoo import api, fields, models


class ProductAttachment(models.Model):
    _name = 'product.attachment'
    _description = 'Product attachments'

    product_id = fields.Many2one('product.template', 'Product Template', required=True)
    attachment = fields.Binary('Attachment', required=True)
    filename = fields.Char('Filename')
