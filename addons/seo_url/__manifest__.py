{
    'name': 'SEO URLs',
    'version': '1.0',
    'description': 'Permanent public URLs: legacy paths that 301 to the record they now belong to.',
    'category': 'Website',
    'author': 'drellxor',
    'depends': [
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/legacy_url_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
