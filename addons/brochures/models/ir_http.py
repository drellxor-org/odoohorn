from odoo import models
from odoo.http import request

MANUAL_DOWNLOADS = '/web/content/brochure.attachment/'


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _post_dispatch(cls, response):
        super()._post_dispatch(response)
        # PDF manuals are going away (diagrams replace them): keep them out of
        # the index now, so removing them later loses nothing in search.
        if request.httprequest.path.startswith(MANUAL_DOWNLOADS):
            response.headers['X-Robots-Tag'] = 'noindex'
