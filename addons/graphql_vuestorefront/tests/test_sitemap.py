import json

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestSitemap(HttpCase):

    def test_lists_exactly_the_live_pages(self):
        env = self.env
        make = env['brochure.category'].create({'name': 'Sitemap Make'})
        filled = env['brochure.category'].create({'name': 'Filled', 'parent_id': make.id})
        empty = env['brochure.category'].create({'name': 'Empty', 'parent_id': make.id})
        live = env['brochure'].create({'name': 'Sitemap Live Model', 'category_ids': [(6, 0, filled.ids)]})
        hidden = env['brochure'].create({'name': 'Sitemap Hidden Model', 'is_published': False})
        article = env['article'].create({'name': 'Sitemap Hidden Article', 'body': 'x', 'is_published': False})

        xml = self.url_open('/sitemap.xml').text

        for path in ('/about', live.website_slug, filled.website_slug, make.website_slug):
            self.assertIn(f'{path}</loc>', xml)
        for path in (hidden.website_slug, article.website_slug, empty.website_slug):
            self.assertNotIn(f'{path}</loc>', xml)

    def test_unpublished_urls_do_not_resolve(self):
        brochure = self.env['brochure'].create({'name': 'Lookup Model'})
        part = self.env['product.template'].create({'name': 'Lookup Part', 'is_published': True})

        def lookup(field, slug):
            response = self.url_open('/graphql/vsf', data=json.dumps(
                {'query': '{ %s(slug: "%s") { id } }' % (field, slug)}),
                headers={'Content-Type': 'application/json'})
            return response.json().get('data', {}).get(field)

        self.assertTrue(lookup('brochure', brochure.website_slug))
        self.assertTrue(lookup('product', part.website_slug))
        brochure.is_published = part.is_published = False
        self.assertIsNone(lookup('brochure', brochure.website_slug))
        self.assertIsNone(lookup('product', part.website_slug))
