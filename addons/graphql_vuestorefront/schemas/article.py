import graphene
from graphql import GraphQLError

from odoo.http import request
from odoo.addons.graphql_vuestorefront.schemas.objects import (
    Article
)


def get_article_list(env, current_page, page_size):
    article_model = env['article'].sudo()

    # First offset is 0 but first page is 1
    if current_page > 1:
        offset = (current_page - 1) * page_size
    else:
        offset = 0

    articles = article_model.search([], order='sequence')

    # If attribute values are selected, we need to get the full list of attribute values and prices
    total_count = len(articles)
    articles = articles[offset:offset + page_size]
    return articles, total_count


class Articles(graphene.ObjectType):
    articles = graphene.List(Article)
    total_count = graphene.Int(required=True)


class ArticleQuery(graphene.ObjectType):
    article = graphene.Field(
        Article,
        id=graphene.Int(default_value=None),
        slug=graphene.String()
    )

    articles = graphene.Field(
        Articles,
        current_page=graphene.Int(default_value=1),
        page_size=graphene.Int(default_value=20),
    )

    @staticmethod
    def resolve_article(self, info, id=None, slug=None):
        env = info.context['env']

        website = env['website'].get_current_website()
        request.website = website

        article_model = env['article'].sudo()

        if id:
            article = article_model.search([('id', '=', id)], limit=1)
        elif slug:
            product = Product.search(['|', ('website_slug', '=', slug), ('website_slug_override', '=', slug)], limit=1)
        else:
            article = article_model
        if not article:
            raise GraphQLError('Article not found')

        return article

    @staticmethod
    def resolve_articles(self, info, current_page, page_size):
        env = info.context["env"]

        website = env['website'].get_current_website()
        request.website = website

        articles, total_count = get_article_list(
            env, current_page, page_size)
        return Articles(articles=articles, total_count=total_count)
