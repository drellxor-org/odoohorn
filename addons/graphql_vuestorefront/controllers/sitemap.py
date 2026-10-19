from xml.sax.saxutils import escape

from odoo import http
from odoo.http import request
from odoo.addons.seo_url.models.legacy_url import is_live, record_url

DEFAULT_WEBSITE_URL = 'https://silverhorn.co.uk'
WEBSITE_URL_PARAM = 'sitemap.website_url'

STATIC_PATHS = [
    '/',
    '/parts',
    '/catalog',
    '/articles',
    '/about',
    '/contact',
]


def _url_tag(loc, lastmod=None):
    parts = ['<url>', f'<loc>{escape(loc)}</loc>']
    if lastmod:
        parts.append(f'<lastmod>{lastmod.strftime("%Y-%m-%d")}</lastmod>')
    parts.append('</url>')
    return ''.join(parts)


def live_pages(env):
    """Every record with a public page, in the final url scheme. Unpublished,
    archived and empty records are left out: their urls answer 404."""
    brochures = env['brochure'].sudo().search([('is_published', '=', True)])
    # A category hub is worth listing only if a published model sits somewhere below it.
    categories = brochures.mapped('category_slug_ids').filtered('is_published')
    return [
        *env['product.template'].sudo().search([('is_published', '=', True)]),
        *brochures,
        *categories,
        *env['article'].sudo().search([('is_published', '=', True)]),
    ]


class Sitemap(http.Controller):

    @http.route('/sitemap.xml', type='http', auth='public', csrf=False, sitemap=False)
    def sitemap_xml(self, **kw):
        env = request.env
        base = env['ir.config_parameter'].sudo().get_param(
            WEBSITE_URL_PARAM, DEFAULT_WEBSITE_URL).rstrip('/')

        out = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        out += [_url_tag(f'{base}{path}') for path in STATIC_PATHS]
        for record in live_pages(env):
            url = is_live(record) and record_url(record)
            if url:
                out.append(_url_tag(f'{base}{url}', lastmod=record.write_date))
        out.append('</urlset>')

        return request.make_response(
            ''.join(out),
            headers=[('Content-Type', 'application/xml; charset=utf-8')],
        )
