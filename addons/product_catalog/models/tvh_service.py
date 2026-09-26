"""TVH REST API client.

POST/inquiries is called from a button on product.template. The response is parsed
into product fields and into auto-created stub products for alternatives and
temporary replacements.

Credentials live in ir.config_parameter (set via Settings → Catalog), with optional
fall-back to TVH_API_* environment variables for .env-driven deployments.
"""

import logging
import os

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_API_URL = 'https://api.tvh.com'
DEFAULT_CONTACT_NAME = 'Silverhorn'
REPLACED_BY_PRICE_CODE = '36'


class TvhService(models.AbstractModel):
    _name = 'tvh.service'
    _description = 'TVH REST API service'

    # ------------------------------------------------------------------------
    #   Config / HTTP
    # ------------------------------------------------------------------------

    @api.model
    def _get_config(self):
        param = self.env['ir.config_parameter'].sudo()
        url = param.get_param('tvh.api.url') or os.environ.get('TVH_API_URL') or DEFAULT_API_URL
        user = param.get_param('tvh.api.username') or os.environ.get('TVH_API_USERNAME')
        password = param.get_param('tvh.api.password') or os.environ.get('TVH_API_PASSWORD')
        customer_code = param.get_param('tvh.customer_code') or os.environ.get('TVH_CUSTOMER_CODE')
        contact_name = (param.get_param('tvh.customer_contact_name')
                        or os.environ.get('TVH_CUSTOMER_CONTACT_NAME')
                        or DEFAULT_CONTACT_NAME)
        if not (user and password and customer_code):
            raise UserError(_('TVH API credentials are not configured. '
                              'Set tvh.api.username, tvh.api.password and tvh.customer_code '
                              'in Settings → Catalog (or TVH_API_USERNAME / TVH_API_PASSWORD '
                              '/ TVH_CUSTOMER_CODE environment variables).'))
        return {'url': url.rstrip('/'), 'user': user, 'password': password,
                'customer_code': customer_code, 'contact_name': contact_name}

    @api.model
    def _request(self, method, path, body=None, timeout=300):
        cfg = self._get_config()
        url = f"{cfg['url']}{path}"
        headers = {
            'Accept': '*/*',
            'User-Agent': 'Silverhorn-Odoo/1.0',
        }
        # TVH's gateway expects an XSRF-TOKEN cookie even though the value isn't
        # validated; missing it yields a 403. Matches Insomnia's default behaviour.
        cookies = {'XSRF-TOKEN': 'NOT_USED'}
        _logger.info('[tvh] %s %s as user=%s', method, url, cfg['user'])
        try:
            resp = requests.request(
                method, url,
                auth=(cfg['user'], cfg['password']),
                json=body,
                headers=headers,
                cookies=cookies,
                timeout=timeout,
                allow_redirects=True,
            )
        except requests.RequestException as e:
            raise UserError(_('Could not reach TVH API: %s') % e) from e
        if not resp.ok:
            _logger.warning(
                '[tvh] %s %s -> HTTP %s\n  request body: %s\n  response body: %s',
                method, url, resp.status_code,
                (str(body) if body else '<none>')[:400],
                (resp.text or '')[:400])
            raise UserError(
                _('TVH API call failed (HTTP %s): %s') % (resp.status_code, (resp.text or '')[:300]))
        if not resp.content:
            return None
        return resp.json()

    # ------------------------------------------------------------------------
    #   Inquiry
    # ------------------------------------------------------------------------

    @api.model
    def refresh_product(self, product):
        """Call POST /customers/{customerCode}/inquiries for a single product.template
        and apply the response to it (and any auto-created alternative / replacement).
        """
        product.ensure_one()
        if not (product.make_id and product.default_code):
            raise UserError(_('Product is missing make or default_code; cannot inquire.'))
        cfg = self._get_config()
        quantity = product.minimum_order_quantity or 1.0
        body = {
            'customerCode': cfg['customer_code'],
            'customerContactName': cfg['contact_name'],
            'lines': [{
                'lineNumber': 1,
                'makeCode': product.make_id.code,
                'partNumber': product.default_code,
                'quantity': quantity,
            }],
        }
        path = f"/customers/{cfg['customer_code']}/inquiries"
        result = self._request('POST', path, body=body)
        if not result:
            raise UserError(_('Empty response from TVH /inquiries.'))
        # response is a list of inquiry objects; we sent one line so one object expected
        inquiry = result[0] if isinstance(result, list) else result
        self._apply_inquiry(product, inquiry)

    # ------------------------------------------------------------------------
    #   Response application
    # ------------------------------------------------------------------------

    @api.model
    def _apply_inquiry(self, product, inquiry):
        lines = inquiry.get('lines') or []
        if not lines:
            raise UserError(_('TVH /inquiries response has no lines.'))

        # custLineNumber "1.0" is the original; "1.1"/"1.2"/... are auto-created lines.
        original = next((l for l in lines if str(l.get('custLineNumber') or '').startswith('1.0')),
                        lines[0])
        autoline = [l for l in lines if l is not original]

        # Detect temporary replacement: the original line has priceCode='36' (Replaced by).
        replacement_line = None
        if str(original.get('priceCode') or '') == REPLACED_BY_PRICE_CODE and autoline:
            # The next line (sorted by lineNumber) is the replacement.
            replacement_line = sorted(autoline, key=lambda l: l.get('lineNumber') or 0)[0]
            # Everything else is "alternatives".
            alternative_lines = [l for l in autoline if l is not replacement_line]
        else:
            alternative_lines = autoline

        self._write_line_to_product(product, original)

        # Replacement
        if replacement_line is not None:
            replacement_product = self._upsert_product_from_line(replacement_line)
            self._write_line_to_product(replacement_product, replacement_line)
            product.replaced_by_id = replacement_product.id

        # Alternatives — one-way M2M (original → alternatives)
        alt_ids = []
        for line in alternative_lines:
            alt = self._upsert_product_from_line(line)
            self._write_line_to_product(alt, line)
            alt_ids.append(alt.id)
        if alt_ids:
            product.alternative_product_ids = [(4, aid) for aid in alt_ids]

    @api.model
    def _write_line_to_product(self, product, line):
        avail = self._upsert_availability_code(line.get('availabilityCode'))
        unit = self._upsert_unit_code(line.get('unitCode'), line.get('isoUnitCode'))

        price = line.get('price') or 0.0
        vals = {
            'tvh_number': line.get('tvhNumber') or False,
            'tvh_price': price,
            'tvh_list_price': line.get('listPrice') or 0.0,
            # Shop price follows our purchase price; the markup comes from Odoo pricelists.
            'list_price': price or product.tvh_pricefile_price or 0.0,
            # tvh_quantity_in_stock is intentionally NOT touched here — it's owned by
            # the daily Stockfile importer.
            'tvh_quantity_updated_at': fields.Datetime.now(),
            'quality_brand': line.get('qualityBrand') or False,
            'unit_code_id': unit.id if unit else False,
            'stock_unit_matrix_desc': line.get('stockUnitMatrixDesc') or False,
            'availability_code_id': avail.id if avail else False,
            'is_reconditioned': bool(line.get('reconditionedPart')),
            'is_non_returnable': bool(line.get('isNonReturnable')),
            'is_non_cancellable': bool(line.get('isNonCancellable')),
            'is_dangerous_goods': bool(line.get('dangerousGood')),
            'surcharge_amount': line.get('surCharge') or 0.0,
            'environmental_fee': line.get('environmentalFee') or 0.0,
            'minimum_order_quantity': line.get('minimumOrderQuantity') or 1.0,
            'not_orderable_reason': line.get('notOrderableReason') or False,
            'sale_ok': bool(line.get('orderable')),
            'purchase_ok': bool(line.get('orderable')),
        }
        # Dimensions
        for src, dst in (('weightInKG', 'weight'),):
            val = line.get(src)
            if val is not None:
                vals[dst] = val
        for src, dst in (('length', 'length_mm'), ('width', 'width_mm'), ('height', 'height_mm')):
            val = line.get(src)
            if val is not None:
                vals[dst] = val
        # weight_gr from kg
        if line.get('weightInKG') is not None:
            vals['weight_gr'] = (line.get('weightInKG') or 0.0) * 1000.0
        product.write(vals)

        # Quantity discounts (replace the whole list)
        product.tvh_quantity_discount_ids.unlink()
        for qd in (line.get('quantityDiscounts') or []):
            self.env['product.tvh.quantity.discount'].create({
                'product_tmpl_id': product.id,
                'qty': qd.get('qty') or 0.0,
                'price': qd.get('price') or 0.0,
            })

    @api.model
    def _upsert_product_from_line(self, line):
        """Find or create a product.template matching the (makeCode, partNumber) of a
        response line. The TVH inquiry response only carries makeCode/partNumber, not
        make_description, so a brand-new make is created with name=code and gets a proper
        name on the next catalog file import (or via the cron, if implemented).
        """
        make_code = line.get('makeCode') or ''
        part = line.get('partNumber') or ''
        if not (make_code and part):
            raise UserError(_('TVH response line is missing makeCode or partNumber.'))
        source = self.env.ref('product_catalog.data_source_tvh', raise_if_not_found=False)
        Make = self.env['product.make'].sudo()
        make = Make.search([('code', '=', make_code),
                            ('data_source_id', '=', source.id if source else False)], limit=1)
        if not make:
            make = Make.create({
                'code': make_code,
                'name': make_code,
                'data_source_id': source.id if source else False,
            })
        Tmpl = self.env['product.template'].sudo()
        tmpl = Tmpl.search([('default_code', '=', part), ('make_id', '=', make.id)], limit=1)
        if not tmpl:
            tmpl = Tmpl.create({
                'name': line.get('productName') or part,
                'default_code': part,
                'make_id': make.id,
                'data_source_id': source.id if source else False,
                'type': 'product',
                'sale_ok': True,
                'purchase_ok': True,
            })
        return tmpl

    @staticmethod
    def _format_stock(qty):
        """TVH Stockfile convention: 'NO' for 0, '+10' for >10, integer otherwise."""
        if qty is None:
            return False
        try:
            val = int(float(qty))
        except (TypeError, ValueError):
            return str(qty)
        if val <= 0:
            return 'NO'
        if val > 10:
            return '+10'
        return str(val)

    @api.model
    def _upsert_availability_code(self, code):
        if not code:
            return False
        Code = self.env['tvh.availability.code'].sudo()
        rec = Code.search([('code', '=ilike', code)], limit=1)
        if not rec:
            rec = Code.create({'code': code})
        return rec

    @api.model
    def _upsert_unit_code(self, code, iso_code=None):
        if not code:
            return False
        Code = self.env['tvh.unit.code'].sudo()
        rec = Code.search([('code', '=ilike', code)], limit=1)
        if not rec:
            rec = Code.create({'code': code, 'iso_code': iso_code or False})
        elif iso_code and not rec.iso_code:
            rec.iso_code = iso_code
        return rec

    # ------------------------------------------------------------------------
    #   Cron: refresh code tables from TVH GET endpoints
    # ------------------------------------------------------------------------

    @api.model
    def cron_refresh_codes(self):
        for path, model_name, key in (
            ('/availability-codes', 'tvh.availability.code', 'availability'),
            ('/unit-codes', 'tvh.unit.code', 'unit'),
        ):
            try:
                data = self._request('GET', path)
            except UserError as e:
                _logger.warning('[tvh] could not fetch %s: %s', path, e)
                continue
            if not isinstance(data, list):
                _logger.warning('[tvh] unexpected %s payload: %s', path, type(data))
                continue

            # The endpoint returns one row per (code, language). Keep only English rows;
            # codes without an EN row are skipped.
            canonical = {}
            for item in data:
                if item.get('language') != 'EN':
                    continue
                code = item.get('code') or item.get('availabilityCode') or item.get('unitCode')
                if not code:
                    continue
                canonical[code] = item

            Code = self.env[model_name].sudo()
            for code, item in canonical.items():
                description = item.get('description') or item.get('label') or False
                iso = item.get('isoUnitCode') or item.get('isoCode')
                rec = Code.search([('code', '=', code)], limit=1)
                vals = {'description': description}
                if model_name == 'tvh.unit.code' and iso:
                    vals['iso_code'] = iso
                if rec:
                    rec.write(vals)
                else:
                    vals['code'] = code
                    Code.create(vals)
            _logger.info('[tvh] refreshed %s (%s unique codes from %s rows)',
                         key, len(canonical), len(data))
