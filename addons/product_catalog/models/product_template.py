import re

from odoo import api, fields, models
from odoo.addons.seo_url.models.slug_mixin import slugify

# Final part url, see docs/seo_tasks.md "P0 · Final URL scheme".
PART_SLUG_RE = re.compile(r'^/parts/[a-z0-9-]+/[a-z0-9-]+$')


class ProductTemplate(models.Model):
    _name = 'product.template'
    _inherit = ['product.template', 'website.seo.metadata', 'website.published.mixin', 'seo.slug.mixin']

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

    # --- website slug + JSON-LD ----------------------------------------------------
    # Assigned once at creation by seo.slug.mixin, stored under en_US only: Odoo
    # reads and searches other languages through the en_US fallback.
    website_slug = fields.Char('Website slug', translate=True, copy=False)
    _slug_pattern = PART_SLUG_RE.pattern
    json_ld = fields.Char('JSON-LD')

    def _slug_candidates(self):
        # /parts/{make}/{part no}-{name}: make + part number is the TVH key and is
        # unique; the name is there for people, frozen like the rest.
        make = slugify(self.make_id.name) or 'misc'
        head = '-'.join(filter(None, [slugify(self.default_code) or str(self.id), slugify(self.name)]))
        return [f'/parts/{make}/{head}']

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
        """Give every part without a final url one: no slug yet, or an older
        format (/product/…, /parts/{name}-{id}) that was never public on prod.
        Idempotent, runs on every update via data/backfill.xml."""
        self.env.cr.execute("SELECT id, website_slug->>'en_US' FROM product_template")
        stale = [pid for pid, slug in self.env.cr.fetchall() if not slug or not PART_SLUG_RE.match(slug)]
        self.with_context(active_test=False).browse(stale)._assign_slugs()
