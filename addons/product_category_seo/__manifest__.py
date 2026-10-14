{
    'name': 'Page category seo',
    'version': '1.0',
    # Only the fields: what someone writes there overrides the storefront's page
    # template. Nothing is generated (it used to fill every record with
    # "Order spares and service for …", which then hid the real template).
    'description': "Adds seo fields to products and categories",
    'category': 'Sales/Sales',
    'author': 'drellxor',
    'depends': [
        'simplify_odoo',
        'article',
        'website_sale'
    ],
    'data': [
        'views/views.xml'
    ],
    'installable': True,
    'auto_install': False
}
