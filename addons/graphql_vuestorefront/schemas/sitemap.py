import graphene


class SitemapQuery(graphene.ObjectType):
    sitemap = graphene.List(graphene.String)

    @staticmethod
    def resolve_sitemap(self, info):
        env = info.context['env']

        categories = env['product.public.category'].sudo().search([])
        products = env['product.product'].sudo().search([])
        articles = env['article'].sudo().search([])

        result = []
        for item in [categories, products, articles]:
            result += [i.website_slug for i in item]

        return result

