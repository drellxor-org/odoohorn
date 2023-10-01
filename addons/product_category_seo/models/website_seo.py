from odoo import models, api


class SeoMetadata(models.AbstractModel):
    _inherit = 'website.seo.metadata'

    def get_website_meta(self):
        meta = super(SeoMetadata, self).get_website_meta()
        meta['keywords'] = self.website_meta_keywords
        return meta

    def init_record_metadata(self):
        self.ensure_one()

    @api.model
    def init_metadata(self):
        records = self.search([])
        for record in records:
            record.init_record_metadata()
