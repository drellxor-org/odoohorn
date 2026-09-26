import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

HIDDEN_TOP_LEVEL_NAMES = [
    'Email Marketing',
    'Discuss',
    'Contacts',
    'Calendar',
    'CRM',
    'Dashboards',
    'Inventory',
    'Invoicing',
    'Link Tracker',
    'Site',
    'Pricelists',
    'Attributes',
    'Product Tags',
    'Discount & Loyalty',
    'Gift cards & eWallet',
    'Website',
]

# Belt-and-suspenders: also target by xmlid in case the translated-name search
# misses a row (e.g. utm.menu_link_tracker_root vs link_tracker.link_tracker_menu_main).
HIDDEN_XMLIDS = [
    'utm.menu_link_tracker_root',
    'link_tracker.link_tracker_menu_main',
    'website.menu_website_configuration',
    # Sales → Products; Catalog → Products replaces it (by xmlid: the name clashes)
    'sale.product_menu_catalog',
]

# Menus that we explicitly want visible even if older installs hid them.
RESTORE_NAMES = [
    'Sales',
]


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def simplify_deactivate_menus(self):
        """Deactivate the top-level menus we don't want users to see, and re-activate
        anything in RESTORE_NAMES (so we can pull menus back if we hid them by mistake
        on an earlier install). Runs on install (post_init) and every -u simplify_odoo
        (via the <function> in data/hide_menus.xml).
        """
        # Match by name (translated Char) — works for most menus.
        by_name = self.search([('name', 'in', HIDDEN_TOP_LEVEL_NAMES), ('active', '=', True)])
        # Match by xmlid — covers rows whose translated name doesn't match in en_US.
        by_xmlid = self.browse([])
        for xmlid in HIDDEN_XMLIDS:
            rec = self.env.ref(xmlid, raise_if_not_found=False)
            if rec and rec.active:
                by_xmlid |= rec
        to_disable = by_name | by_xmlid
        if to_disable:
            _logger.info('[simplify_odoo] deactivating menus: %s',
                         [(m.id, m.name) for m in to_disable])
            to_disable.write({'active': False})

        # Restore anything we want visible again.
        to_enable = self.with_context(active_test=False).search([
            ('name', 'in', RESTORE_NAMES), ('active', '=', False)])
        if to_enable:
            _logger.info('[simplify_odoo] re-activating menus: %s',
                         [(m.id, m.name) for m in to_enable])
            to_enable.write({'active': True})
