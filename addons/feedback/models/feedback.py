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
    website = fields.Many2one('website', 'Website')

    @api.model_create_multi
    def create(self, vals_list):
        record = super(Feedback, self).create(vals_list)

        email_template_customer = self.env.ref('feedback.mail_feedback_confirmation')
        email_template_customer.send_mail(record.id, force_send=True)

        email_template_company = self.env.ref('feedback.mail_feedback_to_company')
        email_template_company.send_mail(record.id, force_send=True)

        return record

