{
    'name': 'Articles',
    'version': '1.0',
    'description': "Adds articles",
    'category': 'Sales/Sales',
    'author': 'drellxor',
    'depends': [
        'simplify_odoo',
        'seo_url',
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/article_views.xml',
        'data/slugs.xml',
    ],
    'installable': True,
    'auto_install': False
}
