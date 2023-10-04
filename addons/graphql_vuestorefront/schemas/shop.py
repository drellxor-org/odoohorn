# -*- coding: utf-8 -*-
# Copyright 2023 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import graphene
from odoo.addons.graphql_vuestorefront.schemas.objects import Order, Partner
from odoo.addons.website_mass_mailing.controllers.main import MassMailController
from odoo.http import request
from graphql import GraphQLError


class Cart(graphene.Interface):
    order = graphene.Field(Order)


class CartData(graphene.ObjectType):
    class Meta:
        interfaces = (Cart,)


class ShoppingCartQuery(graphene.ObjectType):
    cart = graphene.Field(
        Cart,
    )

    @staticmethod
    def resolve_cart(self, info):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=True)
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = website.sale_get_order(force_create=True)
        if order:
            order.order_line.filtered(lambda l: not l.product_id.active).unlink()
        return CartData(order=order)


class CartAddItem(graphene.Mutation):
    class Arguments:
        product_id = graphene.Int(required=True)
        quantity = graphene.Int(required=True)
        machine_serial = graphene.String()
        part_number = graphene.String()
        commentary = graphene.String()

    Output = CartData

    @staticmethod
    def mutate(self, info, product_id, quantity, machine_serial, part_number, commentary):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)
        # Forcing the website_id to be passed to the Order
        order.write({'website_id': website.id})

        # Evaluate product
        template = env['product.template'].browse(product_id)
        if not template:
            raise GraphQLError(f'Product {product_id} not found')
        selling_product = env['product.template'].search([('parent_template', '=', product_id),
                                                          ('part_number', '=', part_number),
                                                          ('machine_serial', '=', machine_serial)])
        if not selling_product:
            selling_product = env['product.template'].sudo().create({'name': template.name,
                                                                     'parent_template': template.id,
                                                                     'part_number': part_number,
                                                                     'machine_serial': machine_serial})

        order._cart_update(product_id=selling_product.product_variant_ids[0].id, add_qty=quantity, commentary=commentary)
        return CartData(order=order)


class CartUpdateItem(graphene.Mutation):
    class Arguments:
        line_id = graphene.Int(required=True)
        quantity = graphene.Int(required=True)
        machine_serial = graphene.String()
        part_number = graphene.String()
        commentary = graphene.String()

    Output = CartData

    @staticmethod
    def mutate(self, info, line_id, quantity, machine_serial, part_number, commentary):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)
        line = order.order_line.filtered(lambda rec: rec.id == line_id)
        # Reset Warning Stock Message always before a new update
        line.shop_warning = ""

        if line.machine_serial == machine_serial and line.part_number == part_number:
            order._cart_update(product_id=line.product_id.id, line_id=line.id, set_qty=quantity, commentary=commentary)
        else:
            parent_template = line.product_id.product_tmpl_id.parent_template
            # Evaluate product
            template = env['product.template'].search([('parent_template', '=', parent_template.id),
                                                       ('part_number', '=', part_number),
                                                       ('machine_serial', '=', machine_serial)])
            if template:
                product_id = template.product_variant_ids[0].id
            else:
                new_product = env['product.template'].sudo().create({'name': parent_template.name,
                                                                     'parent_template': parent_template.id,
                                                                     'part_number': part_number,
                                                                     'machine_serial': machine_serial})
                product_id = new_product.product_variant_ids[0].id
            line.unlink()
            order._cart_update(product_id=product_id, add_qty=quantity, commentary=commentary)
        return CartData(order=order)


class CartRemoveItem(graphene.Mutation):
    class Arguments:
        line_id = graphene.Int(required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, line_id):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)
        line = order.order_line.filtered(lambda rec: rec.id == line_id)
        line.unlink()
        return CartData(order=order)


class CartClear(graphene.Mutation):
    Output = Order

    @staticmethod
    def mutate(self, info):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)
        order.order_line.sudo().unlink()
        return order


class SetShippingMethod(graphene.Mutation):
    class Arguments:
        shipping_method_id = graphene.Int(required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, shipping_method_id):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)

        order._check_carrier_quotation(force_carrier_id=shipping_method_id)

        return CartData(order=order)


# ---------------------------------------------------#
#      Additional Mutations that can be useful       #
# ---------------------------------------------------#

class ProductInput(graphene.InputObjectType):
    id = graphene.Int(required=True)
    quantity = graphene.Int(required=True)
    machine_serial = graphene.String()
    part_number = graphene.String()
    commentary = graphene.String()


class CartLineInput(graphene.InputObjectType):
    id = graphene.Int(required=True)
    quantity = graphene.Int(required=True)
    machine_serial = graphene.String()
    part_number = graphene.String()
    commentary = graphene.String()


class CartAddMultipleItems(graphene.Mutation):
    class Arguments:
        products = graphene.List(ProductInput, default_value={}, required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, products):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)
        # Forcing the website_id to be passed to the Order
        order.write({'website_id': website.id})
        for product in products:
            product_id = product['id']
            quantity = product['quantity']
            machine_serial = product['machine_serial']
            part_number = product['part_number']
            commentary = product['commentary']
            order._cart_update(product_id=product_id, add_qty=quantity, machine_serial=machine_serial, part_number=part_number, commentary=commentary)
        return CartData(order=order)


class CartUpdateMultipleItems(graphene.Mutation):
    class Arguments:
        lines = graphene.List(CartLineInput, default_value={}, required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, lines):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)
        for line in lines:
            line_id = line['id']
            quantity = line['quantity']
            machine_serial = line['machine_serial']
            part_number = line['part_number']
            commentary = line['commentary']
            line = order.order_line.filtered(lambda rec: rec.id == line_id)
            # Reset Warning Stock Message always before a new update
            line.shop_warning = ""
            order._cart_update(product_id=line.product_id.id, line_id=line.id, set_qty=quantity, machine_serial=machine_serial, part_number=part_number, commentary=commentary)
        return CartData(order=order)


class CartRemoveMultipleItems(graphene.Mutation):
    class Arguments:
        line_ids = graphene.List(graphene.Int, required=True)

    Output = CartData

    @staticmethod
    def mutate(self, info, line_ids):
        env = info.context["env"]
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)
        for line_id in line_ids:
            line = order.order_line.filtered(lambda rec: rec.id == line_id)
            line.unlink()
        return CartData(order=order)


class CreateUpdatePartner(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()
        comment = graphene.String()

    Output = Partner

    @staticmethod
    def mutate(self, info, name, email, phone, comment):
        env = info.context['env']
        website = env['website'].get_current_website()
        request.website = website
        order = website.sale_get_order(force_create=1)

        data = {
            'name': name,
            'email': email,
            'phone': phone,
            'comment': comment
        }

        partner = order.partner_id

        # Is public user
        if partner.id == website.user_id.sudo().partner_id.id:
            partner = env['res.partner'].sudo().create(data)

            order.write({
                'partner_id': partner.id,
                'partner_invoice_id': partner.id,
                'partner_shipping_id': partner.id,
            })
        else:
            partner.write(data)

        return partner


class ShopMutation(graphene.ObjectType):
    cart_add_item = CartAddItem.Field(description="Add Item")
    cart_update_item = CartUpdateItem.Field(description="Update Item")
    cart_remove_item = CartRemoveItem.Field(description="Remove Item")
    cart_clear = CartClear.Field(description="Cart Clear")
    cart_add_multiple_items = CartAddMultipleItems.Field(description="Add Multiple Items")
    cart_update_multiple_items = CartUpdateMultipleItems.Field(description="Update Multiple Items")
    cart_remove_multiple_items = CartRemoveMultipleItems.Field(description="Remove Multiple Items")
    set_shipping_method = SetShippingMethod.Field(description="Set Shipping Method on Cart")
    create_update_partner = CreateUpdatePartner.Field(description="Create or update a partner for guest checkout")
