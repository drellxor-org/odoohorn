{
    'name': 'Simplify Odoo',
    'version': '1.0',
    'description': "Hides modules, menus and fields",
    'category': 'Website',
    'author': 'drellxor',
    'depends': [
        'mail',
        'stock',
        'website_sale'
    ],
    'data': [
        'views/product_views.xml',
    ],
    'post_init_hook': 'post_init',
    'installable': True,
    'auto_install': False
}
