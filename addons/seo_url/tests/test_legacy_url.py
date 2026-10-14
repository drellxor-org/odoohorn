from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import mute_logger

from ..models.legacy_url import normalize_path


# post_install: the fixture uses product.template's is_published / website_slug,
# which come from modules that load after this one.
@tagged('post_install', '-at_install')
class TestLegacyUrl(TransactionCase):

    def setUp(self):
        super().setUp()
        self.product = self.env['product.template'].create({'name': 'Legacy target', 'is_published': True})
        self.product.website_slug = '/parts/test/legacy-target'
        self.Legacy = self.env['legacy.url']

    def add(self, path, record):
        return self.Legacy.create({'path': path, 'res_model': record._name, 'res_id': record.id})

    def test_normalize_path(self):
        self.assertEqual(normalize_path('Product/Foo-1/'), '/product/foo-1')
        self.assertEqual(normalize_path('/'), '/')

    def test_map_points_at_current_url(self):
        self.add('/Product/Old-Thing-571/', self.product)
        self.assertEqual(self.Legacy.redirect_map()['/product/old-thing-571'], '/parts/test/legacy-target')

        # The target follows the record, not a stored url.
        self.product.website_slug = '/parts/test/renamed'
        self.assertEqual(self.Legacy.redirect_map()['/product/old-thing-571'], '/parts/test/renamed')

    def test_dead_or_circular_targets_are_left_out(self):
        self.add('/product/unpublished-1', self.product)
        self.assertNotIn('/parts/test/legacy-target', self.Legacy.redirect_map(), 'no self-redirect')

        self.product.is_published = False
        self.assertNotIn('/product/unpublished-1', self.Legacy.redirect_map())

        self.product.is_published = True
        self.assertEqual(self.Legacy.redirect_map()['/product/unpublished-1'], '/parts/test/legacy-target')

        self.product.unlink()
        self.assertNotIn('/product/unpublished-1', self.Legacy.redirect_map())

    def test_path_is_unique(self):
        self.add('/test-only/unique-path', self.product)
        with self.assertRaises(Exception), self.cr.savepoint(), mute_logger('odoo.sql_db'):
            self.add('/Test-Only/Unique-Path/', self.product)

    def test_editing_a_slug_keeps_the_old_url_working(self):
        self.product.website_slug = '/Parts/Test/New-Name/'
        self.assertEqual(self.product.website_slug, '/parts/test/new-name', 'normalised')
        self.assertEqual(self.Legacy.redirect_map()['/parts/test/legacy-target'], '/parts/test/new-name')

        # Back to its own old url: live again, no longer a redirect.
        self.product.website_slug = '/parts/test/legacy-target'
        self.assertFalse(self.Legacy.search([('path', '=', '/parts/test/legacy-target')]))
        self.assertEqual(self.Legacy.redirect_map()['/parts/test/new-name'], '/parts/test/legacy-target')

    def test_slug_edits_are_validated(self):
        with self.assertRaises(ValidationError):
            self.product.website_slug = '/model/wrong-prefix'
        other = self.env['product.template'].create({'name': 'Other', 'is_published': True})
        with self.assertRaises(ValidationError):
            other.website_slug = '/parts/test/legacy-target'  # another record's url
        self.product.website_slug = '/parts/test/moved'
        with self.assertRaises(ValidationError):
            other.website_slug = '/parts/test/legacy-target'  # another record's old url

    def test_new_records_never_take_an_old_url(self):
        self.add('/parts/misc/x1-dup', self.product)
        dup = self.env['product.template'].create({'name': 'Dup', 'default_code': 'X1'})
        self.assertEqual(dup.website_slug, '/parts/misc/x1-dup-2')


@tagged('post_install', '-at_install')
class TestLegacyUrlEndpoint(HttpCase):

    def test_endpoint(self):
        product = self.env['product.template'].create({'name': 'Endpoint target', 'is_published': True})
        product.website_slug = '/parts/test/endpoint-target'
        self.env['legacy.url'].create({'path': '/product/old-2', 'res_model': product._name, 'res_id': product.id})

        response = self.url_open('/legacy-urls.json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('/product/old-2'), '/parts/test/endpoint-target')
