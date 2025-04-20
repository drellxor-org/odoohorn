from odoo import models


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'website.seo.metadata']

    def init_record_metadata(self):
        super().init_record_metadata()

        manufacturers = self.public_categ_ids if self.public_categ_ids else []
        manufacturer_names = []
        for manufacturer in manufacturers:
            current_manufacturer = manufacturer
            while current_manufacturer is not None and current_manufacturer.parent_id:
                current_manufacturer = current_manufacturer.parent_id
            if current_manufacturer:
                manufacturer_names.append(current_manufacturer.name)
        seo_manufacturer = ', '.join(manufacturer_names) or 'None'

        if not self.website_meta_title:
            self.website_meta_title = f'{seo_manufacturer} {self.name}'
        if not self.website_meta_description:
            self.website_meta_description = f'Order spares and service for {seo_manufacturer} {self.name}'
        if not self.website_meta_keywords:
            self.website_meta_keywords = f'{seo_manufacturer}, {self.name}, spares, service, plant, machinery, worldwide, order, delivery'
