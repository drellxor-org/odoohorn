from odoo import http
from odoo.http import request
from xml.sax.saxutils import escape

DEFAULT_WEBSITE_URL = 'https://silverhorn.co.uk'
WEBSITE_URL_PARAM = 'sitemap.website_url'

STATIC_PATHS = [
    '/',
    '/parts',
    '/catalog',
    '/articles',
    '/contact',
]


def _slug(record):
    """Return the record's website_slug as a plain string, with a leading
    slash so it can be concatenated onto the site base URL.

    website_slug already resolves the *_override in the compute; we only
    have to normalize the format (translated fields can arrive as
    {'en_US': ...} dicts; user-entered overrides may omit the leading /)."""
    slug = record.website_slug
    if isinstance(slug, dict):
        slug = slug.get('en_US') or next(iter(slug.values()), None)
    if not slug:
        return None
    return slug if slug.startswith('/') else f'/{slug}'


def _url_tag(loc, lastmod=None):
    parts = ['<url>', f'<loc>{escape(loc)}</loc>']
    if lastmod:
        parts.append(f'<lastmod>{lastmod.strftime("%Y-%m-%d")}</lastmod>')
    parts.append('</url>')
    return ''.join(parts)


class Sitemap(http.Controller):

    @http.route('/sitemap.xml', type='http', auth='public', csrf=False, sitemap=False)
    def sitemap_xml(self, **kw):
        env = request.env
        base = env['ir.config_parameter'].sudo().get_param(
            WEBSITE_URL_PARAM, DEFAULT_WEBSITE_URL).rstrip('/')

        out = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

        for path in STATIC_PATHS:
            out.append(_url_tag(f'{base}{path}'))

        products = env['product.template'].sudo().with_context(lang='en_US').search(
            [('website_published', '=', True)])
        for p in products:
            slug = _slug(p)
            if slug:
                out.append(_url_tag(f'{base}{slug}', lastmod=p.write_date))

        brochures = env['brochure'].sudo().with_context(lang='en_US').search(
            [('active', '=', True)])
        for b in brochures:
            slug = _slug(b)
            if slug:
                out.append(_url_tag(f'{base}{slug}', lastmod=b.write_date))

        categories = env['brochure.category'].sudo().with_context(lang='en_US').search([])
        for c in categories:
            slug = _slug(c)
            if slug:
                out.append(_url_tag(f'{base}{slug}', lastmod=c.write_date))

        articles = env['article'].sudo().search([])
        for a in articles:
            slug = _slug(a)
            if slug:
                out.append(_url_tag(f'{base}{slug}', lastmod=a.write_date))

        out.append('</urlset>')
        return request.make_response(
            ''.join(out),
            headers=[('Content-Type', 'application/xml; charset=utf-8')],
        )
