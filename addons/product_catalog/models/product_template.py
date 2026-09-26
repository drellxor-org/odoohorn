from odoo import api, fields, models
from odoo.addons.http_routing.models.ir_http import slugify


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'website.seo.metadata', 'website.published.mixin']

    data_source_id = fields.Many2one('data.source', 'Data source', ondelete='restrict')
    make_id = fields.Many2one('product.make', 'Make', ondelete='restrict', index=True)

    is_dangerous_goods = fields.Boolean('Dangerous goods')

    # Catalog values preserved in their original units.
    weight_gr = fields.Float('Packaged weight (g)')
    length_mm = fields.Float('Packaged length (mm)')
    width_mm = fields.Float('Packaged width (mm)')
    height_mm = fields.Float('Packaged height (mm)')

    # Set by the daily TVH import (tvh.import) to detect changed rows.
    tvh_source_digest = fields.Char('TVH catalog row digest', copy=False, readonly=True)
    tvh_image_url = fields.Char('TVH image URL', copy=False, readonly=True)
    tvh_pricefile_price = fields.Float(
        'TVH price file price', copy=False, readonly=True,
        help='Last value the TVH price file gave this part. tvh_price follows the file only '
             'when this changes, so a manual refresh from TVH is not overwritten.')

    application_ids = fields.One2many(
        'product.application', 'product_tmpl_id', 'Applications')

    # --- website slug + JSON-LD (mirrors graphql_vuestorefront's pattern) ----------
    website_slug = fields.Char(
        'Website slug', compute='_compute_website_slug', store=True, readonly=True, translate=True)
    website_slug_override = fields.Char('User-defined website slug')
    json_ld = fields.Char('JSON-LD')

    @api.depends('name', 'website_slug_override')
    def _compute_website_slug(self):
        langs = self.env['res.lang'].search([])
        for product in self:
            for lang in langs:
                product_lang = product.with_context(lang=lang.code)
                if not product_lang.id:
                    product_lang.website_slug = None
                    continue
                if product_lang.website_slug_override:
                    product_lang.website_slug = product_lang.website_slug_override
                else:
                    slug_name = slugify(product_lang.name or '').strip().strip('-')
                    product_lang.website_slug = '/product/{}-{}'.format(slug_name, product_lang.id)

    # --- TVH inquiry result fields -------------------------------------------------
    tvh_number = fields.Integer('TVH number', index=True,
                                help='TVH internal product id returned by /inquiries.')
    tvh_price = fields.Float('TVH price (base)',
                             help='Negotiated customer price returned by TVH, before surcharges.')
    tvh_list_price = fields.Float('TVH list price',
                                  help='TVH public list price.')
    tvh_quantity_in_stock = fields.Char('TVH stock (UK)')
    tvh_quantity_in_stock_be = fields.Char('TVH stock (BE)')
    tvh_quantity_updated_at = fields.Datetime('TVH last refresh')

    quality_brand = fields.Char('Quality brand')
    unit_code_id = fields.Many2one('tvh.unit.code', 'Unit code', ondelete='restrict')
    stock_unit_matrix_desc = fields.Char('Stock unit description',
                                         help='Human-readable unit, e.g. "box 10 piece" or "Meter".')
    availability_code_id = fields.Many2one('tvh.availability.code', 'Availability code',
                                           ondelete='restrict')

    is_reconditioned = fields.Boolean('Reconditioned (reman)')
    is_non_returnable = fields.Boolean('Non-returnable')
    is_non_cancellable = fields.Boolean('Non-cancellable')

    surcharge_amount = fields.Float('Surcharge / core charge')
    environmental_fee = fields.Float('Environmental fee')

    minimum_order_quantity = fields.Float('Minimum order quantity', default=1.0)
    not_orderable_reason = fields.Char('Not orderable reason')

    tvh_quantity_discount_ids = fields.One2many(
        'product.tvh.quantity.discount', 'product_tmpl_id', 'Quantity discounts')

    # --- replacement chain --------------------------------------------------------
    replaced_by_id = fields.Many2one(
        'product.template', 'Replaced by', ondelete='set null', index=True,
        help='If TVH replaced this part by another, the immediate successor.')
    latest_product_id = fields.Many2one(
        'product.template', 'Latest product', compute='_compute_latest_product_id',
        store=True, recursive=True,
        help='Follows the replaced_by chain to the final (un-replaced) product.')

    @api.depends('replaced_by_id', 'replaced_by_id.latest_product_id')
    def _compute_latest_product_id(self):
        for rec in self:
            cur = rec
            seen = set()
            while cur.replaced_by_id and cur.replaced_by_id.id not in seen:
                seen.add(cur.id)
                cur = cur.replaced_by_id
            rec.latest_product_id = cur if cur != rec else False

    def action_refresh_from_tvh(self):
        for rec in self:
            self.env['tvh.service'].refresh_product(rec)
        return True

    @api.model
    def _init_backfill_website_slug(self):
        """Force the stored compute for any product.template that still has an empty
        website_slug (e.g. records that pre-date this field). Idempotent — safe to call
        repeatedly via a <function> element on each module update.
        """
        missing = self.with_context(active_test=False).search([('website_slug', '=', False)])
        if missing:
            missing._compute_website_slug()
