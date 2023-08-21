import os
import graphene
from graphene.types import generic


class FacebookQuery(graphene.ObjectType):
    feed = generic.GenericScalar()

    @staticmethod
    def resolve_feed(self, info):

        return website.company_id
