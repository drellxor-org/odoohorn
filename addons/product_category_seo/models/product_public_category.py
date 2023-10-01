from odoo import models


class ProductPublicCategory(models.Model):
    _name = 'product.public.category'
    _inherit = ['product.public.category', 'website.seo.metadata']

    def init_record_metadata(self):
        super().init_record_metadata()

        categories = []
        current_category = self
        while current_category:
            categories.insert(0, current_category.name)
            current_category = current_category.parent_id

        category = ' '.join(categories)
        keywords = ', '.join(categories)

        if not self.website_meta_title:
            self.website_meta_title = category
        if not self.website_meta_description:
            self.website_meta_description = f'Order spares and service for {category}'
        if not self.website_meta_keywords:
            self.website_meta_keywords = f'{keywords}, spares, service, plant, machinery, worldwide, order, delivery'
