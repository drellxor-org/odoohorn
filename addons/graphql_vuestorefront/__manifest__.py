# -*- coding: utf-8 -*-
# Copyright 2023 ODOOGAP/PROMPTEQUATION LDA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    'name': 'Vue Storefront Api',
    'version': '16.0.1.0.0',
    'summary': 'Vue Storefront API',
    'description': """Vue Storefront API Integration""",
    'category': 'Website',
    'license': 'LGPL-3',
    'author': 'OdooGap',
    'website': 'https://www.odoogap.com/',
    'depends': [
        'graphql_base',
        'website_sale_wishlist',
        'website_sale_delivery',
        'website_mass_mailing',
        'website_sale_loyalty',
        'auth_signup',
        'contacts',
        'crm',
        'theme_default',
        'payment_adyen_vsf',
        'article',
        'feedback',
        'order_product_info',
        'page_message',
        'product_attachment',
        'simplify_odoo'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/website_data.xml',
        'data/mail_template.xml',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron_data.xml',
        'data/product_public_category_data.xml',
        'views/product_views.xml',
        'views/website_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False
}
