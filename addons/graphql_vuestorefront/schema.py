# -*- coding: utf-8 -*-
# Copyright 2023 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene

from odoo.addons.graphql_base import OdooObjectType
from odoo.addons.graphql_vuestorefront.schemas import (
    article, country, category, product, order,
    invoice, contact_us, user_profile, sign,
    address, wishlist, shop, payment,
    mailing_list, website, feedback, language, about, sitemap
)


class Query(
    OdooObjectType,
    article.ArticleQuery,
    # country.CountryQuery,
    category.CategoryQuery,
    product.ProductQuery,
    # order.OrderQuery,
    # invoice.InvoiceQuery,
    # user_profile.UserProfileQuery,
    # address.AddressQuery,
    # wishlist.WishlistQuery,
    shop.ShoppingCartQuery,
    # payment.PaymentQuery,
    # mailing_list.MailingContactQuery,
    # mailing_list.MailingListQuery,
    # website.WebsiteQuery,
    language.LanguageQuery,
    about.AboutQuery,
    sitemap.SitemapQuery
):
    pass


class Mutation(
    OdooObjectType,
    # contact_us.ContactUsMutation,
    # user_profile.UserProfileMutation,
    # sign.SignMutation,
    # address.AddressMutation,
    # wishlist.WishlistMutation,
    shop.ShopMutation,
    payment.PaymentMutation,
    # payment.AdyenPaymentMutation,
    # mailing_list.NewsletterSubscribeMutation,
    # order.OrderMutation,
    feedback.FeedbackMutation
):
    pass


schema = graphene.Schema(
    query=Query,
    mutation=Mutation,
    types=[country.CountryList, category.CategoryList, product.ProductList, product.ProductVariantData, order.OrderList,
           invoice.InvoiceList, wishlist.WishlistData, shop.CartData, mailing_list.MailingContactList,
           mailing_list.MailingListList]
)
