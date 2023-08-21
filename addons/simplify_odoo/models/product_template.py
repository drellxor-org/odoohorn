import logging
from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals):
        templates = super(ProductTemplate, self).create(vals)
        # website = self.env['website'].search([], limit=1)
        for template in templates:
            # template.website_id = website.id
            template.is_published = True
            template.list_price = 0
            template.standard_price = 0
            # template.website_published = True

        return templates
