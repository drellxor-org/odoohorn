# -*- coding: utf-8 -*-
# Copyright 2023 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from graphql import GraphQLError
from odoo.http import request
from odoo import _
from odoo.osv import expression

from odoo.addons.graphql_vuestorefront.schemas.objects import (
    SortEnum, Product, Attribute, AttributeValue
)


def get_search_order(sort):
    sorting = ''
    for field, val in sort.items():
        if sorting:
            sorting += ', '
        if field == 'price':
            sorting += 'list_price %s' % val.value
        else:
            sorting += '%s %s' % (field, val.value)

    # Add id as last factor, so we can consistently get the same results
    if sorting:
        sorting += ', id ASC'
    else:
        sorting = 'id ASC'

    return sorting


CATEGORY_LEVEL_KEYS = ('family_ids', 'subfamily_ids', 'subsubfamily_ids')


def get_search_domain(env, search, exclude_facet=None, **kwargs):
    """Build the product search domain.

    `exclude_facet` is one of {'make_ids','family_ids','subfamily_ids','subsubfamily_ids'};
    when set, that filter is dropped (used by facet aggregation so the user sees
    sibling options).
    """
    # Only get published products
    domains = [env['website'].get_current_website().sale_product_domain()]

    # Filter with ids
    if kwargs.get('ids', False):
        domains.append([('id', 'in', kwargs['ids'])])

    # Filter with Category ID
    if kwargs.get('category_id', False):
        domains.append([('public_categ_ids', 'child_of', kwargs['category_id'])])

    # Filter with Category Slug
    if kwargs.get('category_slug', False):
        domains.append([('public_categ_slug_ids.website_slug', '=', kwargs['category_slug'])])

    # Facet filters — nested under filter.facets in the GraphQL input.
    facets = kwargs.get('facets') or {}
    if facets.get('make_ids') and exclude_facet != 'make_ids':
        domains.append([('make_id', 'in', facets['make_ids'])])
    for key in CATEGORY_LEVEL_KEYS:
        if facets.get(key) and exclude_facet != key:
            domains.append([('public_categ_ids', 'child_of', facets[key])])

    # Filter With Name
    if kwargs.get('name', False):
        name = kwargs['name']
        for n in name.split(" "):
            domains.append([('name', 'ilike', n)])

    if search:
        for srch in search.split(" "):
            domains.append([
                '|', '|', ('name', 'ilike', srch), ('description_sale', 'like', srch), ('default_code', 'like', srch)])

    partial_domain = domains.copy()

    # Product Price Filter
    if kwargs.get('min_price', False):
        domains.append([('list_price', '>=', float(kwargs['min_price']))])
    if kwargs.get('max_price', False):
        domains.append([('list_price', '<=', float(kwargs['max_price']))])

    # Deprecated: filter with Attribute Value
    if kwargs.get('attribute_value_id', False):
        domains.append([('attribute_line_ids.value_ids', 'in', kwargs['attribute_value_id'])])

    # Filter with Attribute Value
    if kwargs.get('attrib_values', False):
        attributes = {}
        attributes_domain = []

        for value in kwargs['attrib_values']:
            try:
                value = value.split('-')
                if len(value) != 2:
                    continue

                attribute_id = int(value[0])
                attribute_value_id = int(value[1])
            except ValueError:
                continue

            if attribute_id not in attributes:
                attributes[attribute_id] = []

            attributes[attribute_id].append(attribute_value_id)

        for key, value in attributes.items():
            attributes_domain.append([('attribute_line_ids.value_ids', 'in', value)])

        attributes_domain = expression.AND(attributes_domain)
        domains.append(attributes_domain)

    return expression.AND(domains), expression.AND(partial_domain)


def _category_depth(category):
    """0 for top-level family, 1 for subfamily, 2 for sub-subfamily."""
    return (category.parent_path or '').count('/') - 1


def _aggregate_makes(Product, domain):
    groups = Product.read_group(domain, ['make_id'], ['make_id'])
    makes = Product.env['product.make'].browse([g['make_id'][0] for g in groups if g['make_id']])
    counts = {g['make_id'][0]: g['make_id_count'] for g in groups if g['make_id']}
    return [{'id': m.id, 'name': m.name, 'code': m.code, 'count': counts[m.id], 'parent_id': None}
            for m in makes]


def _aggregate_categories(Product, domain):
    """{depth: [facet]} over public_categ_slug_ids, which already includes ancestors."""
    groups = Product.read_group(domain, ['public_categ_slug_ids'], ['public_categ_slug_ids'])
    counts = {g['public_categ_slug_ids'][0]: g['public_categ_slug_ids_count']
              for g in groups if g['public_categ_slug_ids']}
    by_depth = {0: [], 1: [], 2: []}
    for c in Product.env['product.public.category'].browse(list(counts)):
        depth = _category_depth(c)
        if depth in by_depth:
            by_depth[depth].append({'id': c.id, 'name': c.display_name or c.name,
                                    'parent_id': c.parent_id.id or None,
                                    'count': counts[c.id], 'code': None})
    return by_depth


def get_product_list(env, current_page, page_size, search, sort, **kwargs):
    """Counting, price range and facets run as SQL aggregates: loading every matching
    record to aggregate in Python cost ~1s per query once the 13.5k TVH catalog landed."""
    Product = env['product.template'].sudo()
    domain, partial_domain = get_search_domain(env, search, **kwargs)

    # First offset is 0 but first page is 1
    if current_page > 1:
        offset = (current_page - 1) * page_size
    else:
        offset = 0
    order = get_search_order(sort)
    total_count = Product.search_count(domain)
    paged = Product.search(domain, order=order, offset=offset, limit=page_size)

    # Price range and attribute values ignore the price/attribute filters themselves,
    # so the filter UI can still offer the full range.
    stats = Product.read_group(partial_domain,
                               ['min_price:min(list_price)', 'max_price:max(list_price)'], [])[0]
    attribute_values = env['product.attribute.value'].browse([
        g['variant_attribute_value_ids'][0]
        for g in Product.read_group(partial_domain, ['variant_attribute_value_ids'],
                                    ['variant_attribute_value_ids'])
        if g['variant_attribute_value_ids']])

    # Facets — strict style: all dimensions are computed from the already-filtered
    # product set, so the available options never exceed what the current filter
    # actually contains.
    available_makes = _aggregate_makes(Product, domain)
    categories = _aggregate_categories(Product, domain)

    return (paged, total_count, attribute_values, stats['min_price'] or 0.0, stats['max_price'] or 0.0,
            available_makes, categories[0], categories[1], categories[2])


class ProductFacets(graphene.ObjectType):
    makes = graphene.List(graphene.NonNull(lambda: FacetValue))
    families = graphene.List(graphene.NonNull(lambda: FacetValue))
    subfamilies = graphene.List(graphene.NonNull(lambda: FacetValue))
    subsubfamilies = graphene.List(graphene.NonNull(lambda: FacetValue))


class Products(graphene.Interface):
    products = graphene.List(Product)
    total_count = graphene.Int(required=True)
    attribute_values = graphene.List(AttributeValue)
    min_price = graphene.Float()
    max_price = graphene.Float()
    facets = graphene.Field(ProductFacets)


class ProductList(graphene.ObjectType):
    class Meta:
        interfaces = (Products,)


class FacetFilterInput(graphene.InputObjectType):
    make_ids = graphene.List(graphene.Int)
    family_ids = graphene.List(graphene.Int)
    subfamily_ids = graphene.List(graphene.Int)
    subsubfamily_ids = graphene.List(graphene.Int)


class ProductFilterInput(graphene.InputObjectType):
    ids = graphene.List(graphene.Int)
    category_id = graphene.List(graphene.Int)
    category_slug = graphene.String()
    # Deprecated
    attribute_value_id = graphene.List(graphene.Int)
    attrib_values = graphene.List(graphene.String)
    name = graphene.String()
    min_price = graphene.Float()
    max_price = graphene.Float()
    facets = graphene.Field(FacetFilterInput)


class FacetValue(graphene.ObjectType):
    id = graphene.Int(required=True)
    code = graphene.String()
    name = graphene.String()
    parent_id = graphene.Int()
    count = graphene.Int(required=True)


class ProductSortInput(graphene.InputObjectType):
    id = SortEnum()
    name = SortEnum()
    price = SortEnum()
    popularity = SortEnum()


class ProductVariant(graphene.Interface):
    product = graphene.Field(Product)
    product_template_id = graphene.Int()
    display_name = graphene.String()
    display_image = graphene.Boolean()
    price = graphene.Float()
    list_price = graphene.String()
    has_discounted_price = graphene.Boolean()
    is_combination_possible = graphene.Boolean()


class ProductVariantData(graphene.ObjectType):
    class Meta:
        interfaces = (ProductVariant,)


class ProductQuery(graphene.ObjectType):
    product = graphene.Field(
        Product,
        id=graphene.Int(default_value=None),
        slug=graphene.String(default_value=None),
        barcode=graphene.String(default_value=None),
    )
    products = graphene.Field(
        Products,
        filter=graphene.Argument(ProductFilterInput, default_value={}),
        current_page=graphene.Int(default_value=1),
        page_size=graphene.Int(default_value=20),
        search=graphene.String(default_value=False),
        sort=graphene.Argument(ProductSortInput, default_value={})
    )
    attribute = graphene.Field(
        Attribute,
        required=True,
        id=graphene.Int(),
    )
    product_variant = graphene.Field(
        ProductVariant,
        required=True,
        product_template_id=graphene.Int(),
        combination_id=graphene.List(graphene.Int)
    )

    @staticmethod
    def resolve_product(self, info, id=None, slug=None, barcode=None):
        env = info.context["env"]
        Product = env["product.template"].sudo()

        website = env['website'].get_current_website()
        request.website = website

        if id:
            product = Product.search([('id', '=', id)], limit=1)
        elif slug:
            product = Product.search(['|', ('website_slug', '=', slug), ('website_slug_override', '=', slug)], limit=1)
        elif barcode:
            product = Product.search([('barcode', '=', barcode)], limit=1)
        else:
            product = Product

        if product:
            website = env['website'].get_current_website()
            request.website = website
            if not product.can_access_from_current_website():
                product = Product

        return product

    @staticmethod
    def resolve_products(self, info, filter, current_page, page_size, search, sort):
        env = info.context["env"]

        website = env['website'].get_current_website()
        request.website = website

        (products, total_count, attribute_values, min_price, max_price,
         available_makes, available_families, available_subfamilies,
         available_subsubfamilies) = get_product_list(
            env, current_page, page_size, search, sort, **filter)
        facets = ProductFacets(
            makes=[FacetValue(**f) for f in available_makes],
            families=[FacetValue(**f) for f in available_families],
            subfamilies=[FacetValue(**f) for f in available_subfamilies],
            subsubfamilies=[FacetValue(**f) for f in available_subsubfamilies],
        )
        return ProductList(
            products=products,
            total_count=total_count,
            attribute_values=attribute_values,
            min_price=min_price,
            max_price=max_price,
            facets=facets,
        )

    @staticmethod
    def resolve_attribute(self, info, id):
        return info.context["env"]["product.attribute"].search([('id', '=', id)], limit=1)

    @staticmethod
    def resolve_product_variant(self, info, product_template_id, combination_id):
        env = info.context["env"]

        website = env['website'].get_current_website()
        request.website = website
        pricelist = website.get_current_pricelist()

        product_template = env['product.template'].browse(product_template_id)
        combination = env['product.template.attribute.value'].browse(combination_id)

        variant_info = product_template._get_combination_info(combination, pricelist)

        product = env['product.product'].browse(variant_info['product_id'])

        # Condition to verify if Product exist
        if not product:
            raise GraphQLError(_('Product does not exist'))

        is_combination_possible = product_template._is_combination_possible(combination)

        # Condition to Verify if Product is active or if combination exist
        if not product.active or not is_combination_possible:
            variant_info['is_combination_possible'] = False
        else:
            variant_info['is_combination_possible'] = True

        return ProductVariantData(
            product=product,
            product_template_id=variant_info['product_template_id'],
            display_name=variant_info['display_name'],
            display_image=variant_info['display_image'],
            price=variant_info['price'],
            list_price=variant_info['list_price'],
            has_discounted_price=variant_info['has_discounted_price'],
            is_combination_possible=variant_info['is_combination_possible']
        )


class RefreshProductFromTvh(graphene.Mutation):
    class Arguments:
        product_id = graphene.Int(required=True)

    Output = Product

    @staticmethod
    def mutate(self, info, product_id):
        env = info.context["env"]
        request.website = env["website"].get_current_website()
        product = env["product.template"].sudo().browse(product_id).exists()
        if not product:
            raise GraphQLError(f"Product {product_id} not found")
        env["tvh.service"].refresh_product(product)
        return product


class ProductMutation(graphene.ObjectType):
    refresh_product_from_tvh = RefreshProductFromTvh.Field(
        description="Fetch fresh price / stock / alternatives / replacement info from the TVH inquiry API and apply to the product template.")
