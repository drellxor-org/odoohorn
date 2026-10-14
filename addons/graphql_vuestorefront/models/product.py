# -*- coding: utf-8 -*-
# Copyright 2023 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import re

import requests
from odoo import models, fields, api, tools, _
from odoo.addons.http_routing.models.ir_http import slugify
from odoo.exceptions import ValidationError


GENERATED_META_CLEARED = 'seo.generated_meta_cleared'


def _generated_title(title, name, makes, path=None):
    """product_category_seo's templates: "{root categories, comma-joined} {name}"
    for records, the category path joined by spaces for categories."""
    title, name = title.strip().lower(), name.strip().lower()
    # Compared without slashes and spaces: category names contain " / " too
    # ("3TNC / 4TNC Engine Series"), so the path's separators are ambiguous.
    if path and re.sub(r'[\s/]+', '', title) == re.sub(r'[\s/]+', '', path.lower()):
        return True
    for candidate in {name, re.sub(r' \(.*\)$', '', name)}:
        if candidate and title.endswith(candidate):
            prefix = title[:-len(candidate)].strip()
            if not prefix or all(part.strip() in makes for part in prefix.split(',')):
                return True
    return False


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_public_categ_slug(self, category_ids, category):
        category_ids.append(category.id)

        if category.parent_id:
            category_ids = self._get_public_categ_slug(category_ids, category.parent_id)

        return category_ids

    @api.depends('public_categ_ids')
    def _compute_public_categ_slug_ids(self):
        """ To allow search of website_slug on parent categories """
        cr = self.env.cr

        for product in self:
            category_ids = []

            for category in product.public_categ_ids:
                category_ids = product._get_public_categ_slug(category_ids, category)

            cr.execute("""
                DELETE FROM product_template_product_public_category_slug_rel
                WHERE product_template_id=%s;
            """, (product.id,))

            for category_id in list(dict.fromkeys(category_ids)):
                cr.execute("""
                    INSERT INTO product_template_product_public_category_slug_rel(product_template_id, product_public_category_id)
                    VALUES(%s, %s);
                """, (product.id, category_id,))

    @api.model
    def _init_clear_generated_meta(self):
        """One-off: drop the SEO texts product_category_seo used to generate, so
        the storefront's page template shows instead. Only those: anything else
        in these fields was written by someone and stays. Runs once per
        database (data/seo_cleanup.xml), after the brochures migration copied
        the products' values onto the models."""
        params = self.env['ir.config_parameter'].sudo()
        if params.get_param(GENERATED_META_CLEARED):
            return
        cr = self.env.cr
        cr.execute("""SELECT lower(name->>'en_US') FROM product_public_category WHERE parent_id IS NULL
                      UNION SELECT lower(name->>'en_US') FROM brochure_category WHERE parent_id IS NULL""")
        makes = {row[0] for row in cr.fetchall()} | {'none'}
        for table in ('product_template', 'product_public_category', 'brochure', 'brochure_category', 'article'):
            cr.execute(f"""
                UPDATE {table} SET website_meta_description = NULL
                 WHERE website_meta_description->>'en_US' LIKE 'Order spares and service for %'
                    OR website_meta_description->>'en_US' = 'SilverHorn: Plant machinery spares and service, worldwide delivery'
            """)
            # Generated titles were "{make(s)} {name}", "None {name}" or the name
            # alone. Anything else before the name ("Parts catalogue …") was
            # written by someone. A model renamed "… (early model)" still has
            # the title of its old name.
            path = 'complete_name' if table == 'brochure_category' else 'NULL'
            cr.execute(f"SELECT id, name->>'en_US', website_meta_title->>'en_US', {path} FROM {table} "
                       f"WHERE coalesce(website_meta_title->>'en_US', '') <> ''")
            generated = [row_id for row_id, name, title, full_path in cr.fetchall()
                         if _generated_title(title, name or '', makes, full_path)]
            if generated:
                cr.execute(f'UPDATE {table} SET website_meta_title = NULL WHERE id = ANY(%s)', [generated])
            cr.execute(f"""
                UPDATE {table} SET website_meta_keywords = NULL
                 WHERE website_meta_keywords->>'en_US' LIKE '%spares, service, plant, machinery, worldwide, order, delivery'
            """)
        params.set_param(GENERATED_META_CLEARED, '1')

    @api.depends('product_variant_ids')
    def _compute_variant_attribute_value_ids(self):
        """
        Used to filter attribute values on the website.
        This method computes a list of attribute values from variants of published products.
        This will ensure that the available attribute values on the website filtering will return results.
        By default, Odoo only shows attributes that will return results but doesn't consider that a particular
        attribute value may not have a variant.
        """
        for product in self:
            variants = product.product_variant_ids
            attribute_values = variants.\
                mapped('product_template_attribute_value_ids').\
                mapped('product_attribute_value_id')
            product.variant_attribute_value_ids = [(6, 0, attribute_values.ids)]

    variant_attribute_value_ids = fields.Many2many('product.attribute.value',
                                                   'product_template_variant_product_attribute_value_rel',
                                                   compute='_compute_variant_attribute_value_ids',
                                                   store=True, readonly=True)
    public_categ_slug_ids = fields.Many2many('product.public.category',
                                             'product_template_product_public_category_slug_rel',
                                             compute='_compute_public_categ_slug_ids',
                                             store=True, readonly=True)
    json_ld = fields.Char('JSON-LD')

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        self.env['invalidate.cache'].create_invalidate_cache(self._name, self.ids)
        return res

    def unlink(self):
        self.env['invalidate.cache'].create_invalidate_cache(self._name, self.ids)
        return super(ProductTemplate, self).unlink()

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False,
                              parent_combination=False, only_template=False):
        """ Add discount value and percentage based """
        combination_info = super(ProductTemplate, self)._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
            parent_combination=parent_combination, only_template=only_template)

        discount = 0
        discount_perc = 0
        if combination_info['has_discounted_price'] and product_id:
            discount = combination_info['list_price'] - combination_info['price']
            discount_perc = combination_info['list_price'] and (discount * 100 / combination_info['list_price']) or 0

        combination_info.update({
            'discount': round(discount, 2),
            'discount_perc': int(round(discount_perc, 2)),
        })

        return combination_info


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    website_slug = fields.Char('Website Slug', compute='_compute_website_slug', store=True, readonly=True,
                               translate=True)
    website_slug_override = fields.Char('User-defined website slug')
    json_ld = fields.Char('JSON-LD')

    def unlink(self):
        self.env['invalidate.cache'].create_invalidate_cache(self._name, self.ids)
        return super(ProductPublicCategory, self).unlink()

    @api.depends('name')
    def _compute_website_slug(self):
        langs = self.env['res.lang'].search([])

        for category in self:
            for lang in langs:
                category = category.with_context(lang=lang.code)

                if not category.id:
                    category.website_slug = None
                else:
                    category._slugify_children()

    def _slugify_category(self):
        slug_list = []
        parent_id = self.parent_id
        while parent_id:
            current_slug = slugify(f"{parent_id.name or ''}-{parent_id.id}").strip().strip('-')
            slug_list.insert(0, current_slug)
            parent_id = parent_id.parent_id
        current_slug = slugify(f"{self.name or ''}-{self.id}").strip().strip('-')
        slug_list.append(current_slug)
        return slug_list

    def _slugify_children(self):
        for child in self.child_id:
            child._slugify_children()
        slug_list = self._slugify_category()
        prefix = '/category'
        self.website_slug = f'{prefix}/{"/".join(slug_list)}'

    @api.model
    def calculate_slugs(self):
        categories = self.env['product.public.category'].search([])

        prefix = '/category'
        for category in categories:
            slug_list = category._slugify_category()
            category.website_slug = f'{prefix}/{"/".join(slug_list)}'
