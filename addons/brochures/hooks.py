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
    if 'product.attachment' not in env:
        return
    BrochureAttachment = env['brochure.attachment'].sudo()
    for att in env['product.attachment'].sudo().search([]):
        bid = brochure_map.get(att.product_id.id)
        if not bid:
            continue
        vals = {
            'brochure_id': bid,
            'attachment': att.attachment,
            'filename': att.filename,
        }
        if 'is_published' in att._fields:
            vals['is_published'] = att.is_published
        BrochureAttachment.create(vals)


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


def _cleanup_legacy(env, brochure_map):
    """Try to delete the now-migrated sale.order.line, child product.templates, and parent product.templates.
    Failures (e.g. confirmed-order side effects) are logged but don't abort the install.
    """
    SaleOrderLine = env['sale.order.line'].sudo()
    Product = env['product.template'].sudo()
    ProductAttachment = env.get('product.attachment') and env['product.attachment'].sudo()

    # 1. sale.order.line
    lines = SaleOrderLine.with_context(active_test=False).search([
        ('product_template_id', 'in', list(brochure_map.keys())),
    ])
    for line in lines:
        try:
            line.unlink()
        except Exception as e:
            _logger.warning('[brochures] could not unlink sale.order.line %s: %s', line.id, e)

    # 2. product.attachment (already copied to brochure.attachment)
    if ProductAttachment:
        atts = ProductAttachment.search([('product_id', 'in', list(brochure_map.keys()))])
        try:
            atts.unlink()
        except Exception as e:
            _logger.warning('[brochures] could not unlink some product.attachments: %s', e)

    # 3. child product.templates (parent_template set) — unconditionally
    user_products = _user_defined_ids(env, 'product.template')
    children = user_products.filtered(lambda p: p.parent_template)
    for child in children:
        try:
            child.with_context(active_test=False).unlink()
        except Exception as e:
            _logger.warning('[brochures] could not unlink child product.template %s: %s', child.id, e)

    # 4. parent product.templates that were migrated
    parents = Product.browse(list(brochure_map.keys())).exists().filtered(lambda p: not p.parent_template)
    for parent in parents:
        try:
            parent.with_context(active_test=False).unlink()
        except Exception as e:
            _logger.warning('[brochures] could not unlink product.template %s (%s): %s', parent.id, parent.name, e)
