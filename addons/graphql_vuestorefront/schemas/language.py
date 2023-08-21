import graphene

from odoo.addons.graphql_base import OdooObjectType


class Language(OdooObjectType):
    id = graphene.Int(required=True)
    name = graphene.String()
    code = graphene.String()


class LanguageQuery(graphene.ObjectType):
    languages = graphene.List(
        graphene.NonNull(Language),
    )

    @staticmethod
    def resolve_languages(self, info):
        env = info.context['env']
        lang_model = env['res.lang'].sudo()
        return lang_model.search([('active', '=', True)])
