from odoo import api, SUPERUSER_ID

from . import models


def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.ui.menu'].simplify_deactivate_menus()
