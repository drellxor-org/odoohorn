{
    'name': 'Page category seo',
    'version': '1.0',
    'description': "Adds seo fields to products and categories",
    'category': 'Sales/Sales',
    'author': 'drellxor',
    'depends': [
        'simplify_odoo',
        'article',
        'website_sale'
    ],
    'data': [
        'data/seo.xml',
        'views/views.xml'
    ],
    'installable': True,
    'auto_install': False
}
