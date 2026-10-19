from odoo import http
from odoo.http import request


class LegacyUrls(http.Controller):

    # Read by the frontend's SSR server (refreshed every few minutes), which
    # answers these paths with a 301 before Angular renders anything.
    @http.route('/legacy-urls.json', type='http', auth='public', methods=['GET'],
                csrf=False, sitemap=False)
    def legacy_urls(self):
        return request.make_json_response(request.env['legacy.url'].sudo().redirect_map())
