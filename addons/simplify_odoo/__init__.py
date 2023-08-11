import logging
from odoo import api, SUPERUSER_ID


_logger = logging.getLogger(__name__)


def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    menus = [
        'Email Marketing',
        'Discuss',
        'Contacts',
        'Calendar',
        'CRM',
        'Dashboards',
        'Inventory',
        'Sales',
        'Invoicing',
        'Link Tracker',
        'Site',
        'Pricelists',
        'Attributes',
        'Product Tags',
        'Discount & Loyalty',
        'Gift cards & eWallet'
    ]
    for menu in menus:
        _logger.error(menu)
        odoo_menus = env['ir.ui.menu'].search([('name', '=', menu)])
        for odoo_menu in odoo_menus:
            odoo_menu.write({
                'active': False
            })
