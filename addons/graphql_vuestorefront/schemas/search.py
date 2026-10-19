"""GraphQL `search` + `searchSuggest` queries.

Both queries delegate to the `search.engine` abstract model in models/search_service.py.
The model holds the SQL and parsing logic so the GraphQL layer stays thin.
"""

import graphene
from odoo.http import request

from odoo.addons.graphql_vuestorefront.schemas.objects import (
    Article as _Article,
    Product as _Product,
)
from odoo.addons.graphql_vuestorefront.schemas.brochure import (
    Brochure as _Brochure,
)


SuggestionType = graphene.Enum(
    'SuggestionType', [('PRODUCT', 'PRODUCT'), ('BROCHURE', 'BROCHURE'), ('ARTICLE', 'ARTICLE')])


class ParsedQuery(graphene.ObjectType):
    make = graphene.String()
    model = graphene.String()
    part_number = graphene.String()


class SearchProductsSlice(graphene.ObjectType):
    results = graphene.List(graphene.NonNull(lambda: _Product))
    total_count = graphene.Int(required=True)
    has_more = graphene.Boolean(required=True)


class SearchBrochuresSlice(graphene.ObjectType):
    results = graphene.List(graphene.NonNull(lambda: _Brochure))
    total_count = graphene.Int(required=True)
    has_more = graphene.Boolean(required=True)


class SearchArticlesSlice(graphene.ObjectType):
    results = graphene.List(graphene.NonNull(lambda: _Article))
    total_count = graphene.Int(required=True)
    has_more = graphene.Boolean(required=True)


class SearchResult(graphene.ObjectType):
    parsed_query = graphene.Field(ParsedQuery, required=True)
    products = graphene.Field(SearchProductsSlice, required=True)
    brochures = graphene.Field(SearchBrochuresSlice, required=True)
    articles = graphene.Field(SearchArticlesSlice, required=True)


class Suggestion(graphene.ObjectType):
    type = SuggestionType(required=True)
    id = graphene.Int(required=True)
    name = graphene.String(required=True)
    slug = graphene.String()
    similarity = graphene.Float(required=True)


class SearchQuery(graphene.ObjectType):
    search = graphene.Field(
        SearchResult,
        query=graphene.String(required=True),
        products_page=graphene.Int(default_value=1),
        products_page_size=graphene.Int(default_value=5),
        brochures_page=graphene.Int(default_value=1),
        brochures_page_size=graphene.Int(default_value=5),
        articles_page=graphene.Int(default_value=1),
        articles_page_size=graphene.Int(default_value=5),
    )
    search_suggest = graphene.List(
        graphene.NonNull(Suggestion),
        query=graphene.String(required=True),
        limit=graphene.Int(default_value=8),
    )

    @staticmethod
    def resolve_search(self, info, query, products_page, products_page_size,
                       brochures_page, brochures_page_size,
                       articles_page, articles_page_size):
        env = info.context['env']
        request.website = env['website'].get_current_website()
        engine = env['search.engine']

        parsed = engine.parse_query(query)
        parsed_obj = ParsedQuery(
            make=parsed.get('make') or None,
            model=parsed.get('model') or None,
            part_number=parsed.get('part_number') or None,
        )

        # Single corpus query per entity, raw user query (full_text already contains
        # make / categories / sku / part name, so the trigram match covers everything).
        prods, prods_total = engine.search_products(query, products_page, products_page_size)
        brs, brs_total = engine.search_brochures(query, brochures_page, brochures_page_size)
        arts, arts_total = engine.search_articles(query, articles_page, articles_page_size)

        return SearchResult(
            parsed_query=parsed_obj,
            products=SearchProductsSlice(
                results=prods, total_count=prods_total,
                has_more=(products_page * products_page_size) < prods_total),
            brochures=SearchBrochuresSlice(
                results=brs, total_count=brs_total,
                has_more=(brochures_page * brochures_page_size) < brs_total),
            articles=SearchArticlesSlice(
                results=arts, total_count=arts_total,
                has_more=(articles_page * articles_page_size) < arts_total),
        )

    @staticmethod
    def resolve_search_suggest(self, info, query, limit):
        env = info.context['env']
        request.website = env['website'].get_current_website()
        rows = env['search.engine'].suggest(query, limit=limit)
        return [Suggestion(
            type=row['type'], id=row['id'], name=row['name'],
            slug=row['slug'], similarity=row['similarity'],
        ) for row in rows]
