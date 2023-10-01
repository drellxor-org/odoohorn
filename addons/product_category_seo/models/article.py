from odoo import api, models, fields


class Article(models.Model):
    _name = 'article'
    _inherit = ['article', 'website.seo.metadata']

    def init_record_metadata(self):
        super().init_record_metadata()
        if not self.website_meta_title:
            self.website_meta_title = self.name
        if not self.website_meta_description:
            self.website_meta_description = 'SilverHorn: Plant machinery spares and service, worldwide delivery'
        if not self.website_meta_keywords:
            self.website_meta_keywords = 'spares, service, plant, machinery, worldwide, order, delivery'
