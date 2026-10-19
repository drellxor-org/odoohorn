from unittest.mock import patch

from graphql import GraphQLError

from odoo.addons.website.tools import MockRequest
from odoo.tests import TransactionCase, tagged

from ..schemas.payment import verify_recaptcha

POST = 'odoo.addons.google_recaptcha.models.ir_http.requests.post'


@tagged('post_install', '-at_install')
class TestRecaptcha(TransactionCase):

    def google(self, **answer):
        with patch(POST) as post, MockRequest(self.env):
            post.return_value.json.return_value = answer
            verify_recaptcha(self.env, 'token')

    def test_verdicts(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('recaptcha_private_key', '')
        with MockRequest(self.env):
            verify_recaptcha(self.env, None)  # no key: not checked

        params.set_param('recaptcha_private_key', 'test-secret')
        params.set_param('recaptcha_min_score', '0.5')
        self.google(success=True, score=0.9)
        for answer in ({'success': True, 'score': 0.1},
                       {'success': False, 'error-codes': ['timeout-or-duplicate']}):
            with self.assertRaises(GraphQLError):
                self.google(**answer)
