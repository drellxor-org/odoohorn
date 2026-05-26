from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    tvh_api_url = fields.Char(
        'TVH API URL', config_parameter='tvh.api.url',
        default='https://api.tvh.com')
    tvh_api_username = fields.Char(
        'TVH API username', config_parameter='tvh.api.username')
    tvh_api_password = fields.Char(
        'TVH API password', config_parameter='tvh.api.password')
    tvh_customer_code = fields.Char(
        'TVH customer code', config_parameter='tvh.customer_code')
    tvh_customer_contact_name = fields.Char(
        'TVH customer contact name', config_parameter='tvh.customer_contact_name',
        default='Silverhorn')
