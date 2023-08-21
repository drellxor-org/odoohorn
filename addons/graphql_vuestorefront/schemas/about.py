import graphene

from odoo.addons.graphql_vuestorefront.schemas.objects import (
    Company
)

class AboutQuery(graphene.ObjectType):
    about = graphene.Field(
        Company
    )

    @staticmethod
    def resolve_about(self, info):
        env = info.context['env']
        website = env['website'].get_current_website()
        return website.company_id
