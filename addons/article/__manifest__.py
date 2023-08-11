{
    'name': 'Articles',
    'version': '1.0',
    'description': "Adds articles",
    'category': 'Sales/Sales',
    'author': 'drellxor',
    'depends': [
        'simplify_odoo'
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/article_views.xml'
    ],
    'installable': True,
    'auto_install': False
}
