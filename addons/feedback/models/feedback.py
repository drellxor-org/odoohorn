import logging
from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class Feedback(models.Model):
    _name = 'feedback'
    _description = 'Feedback / Requests'
    _order = "write_date DESC"

    name = fields.Char('Name', required=True)
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    text = fields.Text('Text')

    @api.model_create_multi
    def create(self, vals_list):
        record = super(Feedback, self).create(vals_list)

        email_template = self.env['mail.template'].search([('name', '=', 'Feedback')])
        if email_template:
            email_template.send_mail(record.id, force_send=True)
        else:
            _logger.error('No feedback template initialized, no mail sent')

        return record

