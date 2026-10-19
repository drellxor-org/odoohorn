from odoo import fields, models


class BrochureAttachment(models.Model):
    _name = 'brochure.attachment'
    _description = 'Brochure attachments'
    _inherit = ['website.published.mixin']

    brochure_id = fields.Many2one('brochure', 'Brochure', required=True, ondelete='cascade')
    attachment = fields.Binary('Attachment')
    filename = fields.Char('Filename')

    def _default_is_published(self):
        return True
