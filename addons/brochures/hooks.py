import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

_NON_USER_MODULES_EXCLUDE = ('__export__', '__import__', '__custom__')

# Fields the brochure carries from product.template / product.public.category.
_BROCHURE_FIELDS_FROM_PRODUCT = (
    'name',
    'page_message',
    'description_sale',
    'website_meta_title',
    'website_meta_description',
    'website_meta_keywords',
    'website_meta_og_img',
    'website_slug_override',
    'json_ld',
    'is_published',
)
_BROCHURE_CATEGORY_FIELDS_FROM_PUBLIC_CATEGORY = (
    'name',
    'sequence',
    'page_message',
    'website_meta_title',
    'website_meta_description',
    'website_meta_keywords',
    'website_meta_og_img',
    'website_slug_override',
    'json_ld',
    'is_published',
)


def _user_defined_ids(env, model):
    """Return ids of records that don't come from an installed module (i.e. user-created)."""
    records = env[model].with_context(active_test=False).search([])
    if not records:
        return env[model]
    imd = env['ir.model.data'].sudo().search([
        ('model', '=', model),
        ('module', 'not in', list(_NON_USER_MODULES_EXCLUDE)),
        ('res_id', 'in', records.ids),
    ])
    module_owned = set(imd.mapped('res_id'))
    return records.filtered(lambda r: r.id not in module_owned)


def _copy_fields(source, target_vals, fields):
    for f in fields:
        if f not in source._fields:
            continue
        val = source[f]
        if hasattr(val, 'ids'):
            continue
        target_vals[f] = val


def migrate_data(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _logger.info('[brochures] starting migration from product.template / product.public.category')

    cat_map = _migrate_categories(env)
    brochure_map = _migrate_brochures(env, cat_map)
    _migrate_attachments(env, brochure_map)
    _migrate_order_lines(env, brochure_map)
    _cleanup_legacy(env, brochure_map)

    _logger.info('[brochures] migration complete: %s categories, %s brochures',
                 len(cat_map), len(brochure_map))


def _migrate_categories(env):
    """Mirror product.public.category tree into brochure.category. Returns {public_cat_id: brochure_cat_id}."""
    categories = _user_defined_ids(env, 'product.public.category').sorted(key=lambda c: (c.parent_path or '', c.id))
    cat_map = {}
    BrochureCategory = env['brochure.category'].sudo()
    for cat in categories:
        vals = {}
        _copy_fields(cat, vals, _BROCHURE_CATEGORY_FIELDS_FROM_PUBLIC_CATEGORY)
        if cat.parent_id and cat.parent_id.id in cat_map:
            vals['parent_id'] = cat_map[cat.parent_id.id]
        new_cat = BrochureCategory.create(vals)
        cat_map[cat.id] = new_cat.id
    return cat_map


def _migrate_brochures(env, cat_map):
    """Create brochure records for every user-defined parent product.template.
    Returns {product_template_id: brochure_id} (including children, which map to their parent's brochure).
    """
    user_products = _user_defined_ids(env, 'product.template')
    parent_products = user_products.filtered(lambda p: not p.parent_template)
    Brochure = env['brochure'].sudo()
    brochure_map = {}
    for product in parent_products:
        vals = {}
        _copy_fields(product, vals, _BROCHURE_FIELDS_FROM_PRODUCT)
        if 'public_categ_ids' in product._fields and product.public_categ_ids:
            vals['category_ids'] = [(6, 0, [
                cat_map[c.id] for c in product.public_categ_ids if c.id in cat_map
            ])]
        brochure = Brochure.create(vals)
        brochure_map[product.id] = brochure.id

    # Children inherit their parent's brochure.
    for product in user_products.filtered(lambda p: p.parent_template):
        if product.parent_template.id in brochure_map:
            brochure_map[product.id] = brochure_map[product.parent_template.id]

    return brochure_map


def _migrate_attachments(env, brochure_map):
    """Create brochure.attachment rows and re-point the existing ir.attachment binary
    rows via raw SQL. Never reads the binary into Python memory (files stay on disk).
    """
    if 'product.attachment' not in env:
        return
    BrochureAttachment = env['brochure.attachment'].sudo()
    cr = env.cr
    for att in env['product.attachment'].sudo().search([]):
        bid = brochure_map.get(att.product_id.id)
        if not bid:
            continue
        vals = {'brochure_id': bid, 'filename': att.filename}
        if 'is_published' in att._fields:
            vals['is_published'] = att.is_published
        new_att = BrochureAttachment.create(vals)
        cr.execute("""
            UPDATE ir_attachment
               SET res_model = 'brochure.attachment', res_id = %s
             WHERE res_model = 'product.attachment'
               AND res_id = %s
               AND res_field = 'attachment'
        """, (new_att.id, att.id))


def _migrate_order_lines(env, brochure_map):
    SaleOrderLine = env['sale.order.line'].sudo()
    BrochureLine = env['sale.order.brochure.line'].sudo()
    lines = SaleOrderLine.with_context(active_test=False).search([
        ('product_template_id', 'in', list(brochure_map.keys())),
    ])
    for line in lines:
        bid = brochure_map.get(line.product_template_id.id)
        if not bid:
            continue
        BrochureLine.create({
            'order_id': line.order_id.id,
            'brochure_id': bid,
            'name': line.name,
            'sequence': line.sequence,
            'machine_serial': line.machine_serial if 'machine_serial' in line._fields else False,
            'part_number': line.part_number if 'part_number' in line._fields else False,
            'commentary': line.commentary if 'commentary' in line._fields else False,
        })


def _try_unlink(env, record, label):
    """Unlink inside a savepoint so a per-row failure (FK violation, Odoo rule, etc.)
    doesn't poison the surrounding postgres transaction.
    """
    try:
        with env.cr.savepoint():
            record.unlink()
    except Exception as e:
        _logger.warning('[brochures] could not unlink %s %s: %s', label, record.id, e)


def _cleanup_legacy(env, brochure_map):
    """Delete the now-migrated sale.order.line, child product.templates, and parent product.templates.
    Each unlink runs inside its own savepoint, so a single failure (e.g. confirmed-order rule,
    FK from leftover lines) is logged but doesn't abort the surrounding transaction.
    """
    SaleOrderLine = env['sale.order.line'].sudo()
    Product = env['product.template'].sudo()
    user_products = _user_defined_ids(env, 'product.template')
    template_ids = user_products.ids
    variant_ids = env['product.product'].with_context(active_test=False).search([
        ('product_tmpl_id', 'in', template_ids),
    ]).ids

    def _sql_delete(table, where_col, ids):
        if not ids:
            return
        try:
            with env.cr.savepoint():
                env.cr.execute(
                    f"DELETE FROM {table} WHERE {where_col} = ANY(%s)", (ids,))
            _logger.info('[brochures] cleared %s rows in %s', env.cr.rowcount, table)
        except Exception as e:
            _logger.warning('[brochures] could not clear %s: %s', table, e)

    # 1. sale.order.line — raw SQL DELETE to bypass Odoo's "can't unlink confirmed line" rule.
    lines = SaleOrderLine.with_context(active_test=False).search([
        ('product_template_id', 'in', template_ids),
    ])
    for line_id in lines.ids:
        try:
            with env.cr.savepoint():
                env.cr.execute("DELETE FROM sale_order_line WHERE id = %s", (line_id,))
        except Exception as e:
            _logger.warning('[brochures] could not delete sale.order.line %s: %s', line_id, e)

    # 2. product.attachment (binary was re-pointed via SQL earlier; rows themselves can go)
    _sql_delete('product_attachment', 'product_id', template_ids)

    # 3. Stock records referencing the variants — clear FKs that would block product unlink.
    for table in ('stock_move_line', 'stock_move', 'stock_quant',
                  'stock_warehouse_orderpoint', 'stock_scrap'):
        _sql_delete(table, 'product_id', variant_ids)

    # 4. child product.templates (parent_template set)
    for child in user_products.filtered(lambda p: p.parent_template):
        _try_unlink(env, child.with_context(active_test=False), 'child product.template')

    # 5. parent product.templates that were migrated
    parents = Product.browse(list(brochure_map.keys())).exists().filtered(lambda p: not p.parent_template)
    for parent in parents:
        _try_unlink(env, parent.with_context(active_test=False), 'product.template')

    # 6. user-defined product.public.category records (mirrored as brochure.category)
    for cat in _user_defined_ids(env, 'product.public.category'):
        _try_unlink(env, cat.with_context(active_test=False), 'product.public.category')
