from odoo import models


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'website.seo.metadata']

    def init_record_metadata(self):
        super().init_record_metadata()

        manufacturer = self.public_categ_ids if self.public_categ_ids else None
        while manufacturer is not None and manufacturer.parent_id:
            manufacturer = manufacturer.parent_id
        manufacturer_name = manufacturer.name if manufacturer else 'None'

        if not self.website_meta_title:
            self.website_meta_title = f'{manufacturer_name} {self.name}'
        if not self.website_meta_description:
            self.website_meta_description = f'Order spares and service for {manufacturer_name} {self.name}'
        if not self.website_meta_keywords:
            self.website_meta_keywords = f'{manufacturer_name}, {self.name}, spares, service, plant, machinery, worldwide, order, delivery'
