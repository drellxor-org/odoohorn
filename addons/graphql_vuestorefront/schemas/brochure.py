# -*- coding: utf-8 -*-

import graphene
from graphene.types import generic
from graphql import GraphQLError
from odoo import _
from odoo.http import request

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.http_routing.models.ir_http import slugify


# --------------------- #
#        TYPES          #
# --------------------- #


class BrochureCategory(OdooObjectType):
    id = graphene.Int(required=True)
    name = graphene.String()
    parent = graphene.Field(lambda: BrochureCategory)
    childs = graphene.List(graphene.NonNull(lambda: BrochureCategory))
    slug = graphene.String()
    page_message = graphene.String()
    json_ld = generic.GenericScalar()
    seo_metadata = generic.GenericScalar()
    brochures = graphene.List(graphene.NonNull(lambda: Brochure))

    def resolve_parent(self, info):
        return self.parent_id or None

    def resolve_childs(self, info):
        return self.child_id or None

    def resolve_slug(self, info):
        return self.website_slug_override or self.website_slug or None

    def resolve_brochures(self, info):
        return self.env['brochure'].search([('category_ids', 'in', self.ids)]) or None

    def resolve_json_ld(self, info):
        return self.json_ld or None

    def resolve_seo_metadata(self, info):
        return self.get_website_meta() or None


class BrochureAttachment(OdooObjectType):
    id = graphene.Int(required=True)
    filename = graphene.String()
    url = graphene.String()

    def resolve_url(self, info):
        return f'/web/content/brochure.attachment/{self.id}/attachment/{self.filename or ""}'


class Brochure(OdooObjectType):
    id = graphene.Int(required=True)
    name = graphene.String()
    slug = graphene.String()
    page_message = graphene.String()
    description = graphene.String()
    popularity = graphene.Int()
    categories = graphene.List(graphene.NonNull(BrochureCategory))
    attachments = graphene.List(graphene.NonNull(BrochureAttachment))
    json_ld = generic.GenericScalar()
    seo_metadata = generic.GenericScalar()

    def resolve_slug(self, info):
        return self.website_slug_override or self.website_slug or None

    def resolve_description(self, info):
        return self.description_sale or None

    def resolve_categories(self, info):
        return self.category_ids or None

    def resolve_attachments(self, info):
        return self.attachment_ids.filtered(lambda a: a.is_published) or None

    def resolve_json_ld(self, info):
        return self.json_ld or None

    def resolve_seo_metadata(self, info):
        return self.get_website_meta() or None


class BrochureList(graphene.ObjectType):
    brochures = graphene.List(graphene.NonNull(Brochure))
    total_count = graphene.Int(required=True)


# --------------------- #
#        QUERY          #
# --------------------- #


class BrochureQuery(graphene.ObjectType):
    brochure = graphene.Field(
        Brochure,
        id=graphene.Int(),
        slug=graphene.String(),
    )
    brochures = graphene.Field(
        BrochureList,
        search=graphene.String(default_value=''),
        category_id=graphene.Int(),
        category_slug=graphene.String(),
        page_size=graphene.Int(default_value=20),
        current_page=graphene.Int(default_value=1),
    )

    @staticmethod
    def resolve_brochure(self, info, id=None, slug=None):
        env = info.context['env']
        request.website = env['website'].get_current_website()
        Brochure_ = env['brochure'].sudo()
        if id:
            rec = Brochure_.browse(id).exists()
        elif slug:
            rec = Brochure_.search(
                ['|', ('website_slug', '=', slug), ('website_slug_override', '=', slug)], limit=1)
        else:
            raise GraphQLError(_('Either id or slug is required.'))
        if not rec:
            raise GraphQLError(_('Brochure not found.'))
        return rec

    @staticmethod
    def resolve_brochures(self, info, search, category_id=None, category_slug=None,
                          page_size=20, current_page=1):
        env = info.context['env']
        request.website = env['website'].get_current_website()
        Brochure_ = env['brochure'].sudo()

        domain = [('is_published', '=', True), ('active', '=', True)]
        if category_id:
            domain.append(('category_slug_ids', 'in', [category_id]))
        if category_slug:
            domain.append(('category_slug_ids.website_slug', '=', category_slug))
        if search:
            for token in search.split(' '):
                if token:
                    domain.append('|')
                    domain.append(('name', 'ilike', token))
                    domain.append(('description_sale', 'ilike', token))

        total = Brochure_.search_count(domain)
        offset = (max(current_page, 1) - 1) * page_size
        records = Brochure_.search(domain, limit=page_size, offset=offset, order='sequence, name')
        return BrochureList(brochures=records, total_count=total)


class BrochureCategoryQuery(graphene.ObjectType):
    brochure_category = graphene.Field(
        BrochureCategory,
        id=graphene.Int(),
        slug=graphene.String(),
    )
    brochure_categories = graphene.List(
        graphene.NonNull(BrochureCategory),
        parent_id=graphene.Int(),
        roots_only=graphene.Boolean(default_value=False),
    )

    @staticmethod
    def resolve_brochure_category(self, info, id=None, slug=None):
        env = info.context['env']
        request.website = env['website'].get_current_website()
        Cat = env['brochure.category'].sudo()
        if id:
            rec = Cat.browse(id).exists()
        elif slug:
            rec = Cat.search(
                ['|', ('website_slug', '=', slug), ('website_slug_override', '=', slug)], limit=1)
        else:
            raise GraphQLError(_('Either id or slug is required.'))
        if not rec:
            raise GraphQLError(_('Brochure category not found.'))
        return rec

    @staticmethod
    def resolve_brochure_categories(self, info, parent_id=None, roots_only=False):
        env = info.context['env']
        request.website = env['website'].get_current_website()
        domain = [('is_published', '=', True)]
        if roots_only:
            domain.append(('parent_id', '=', False))
        elif parent_id is not None:
            domain.append(('parent_id', '=', parent_id))
        return env['brochure.category'].sudo().search(domain, order='sequence, name')
