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
        records = self.search(['|', ('website_meta_title', '=', False),
                               '|', ('website_meta_description', '=', False), ('website_meta_keywords', '=', False)])
        for record in records:
            record.init_record_metadata()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.init_record_metadata()
        return records
