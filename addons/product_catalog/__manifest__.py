{
    'name': 'Product Catalog',
    'version': '1.0',
    'description': 'External catalog metadata for product.template: data source, make, applications, packaged dimensions.',
    'category': 'Sales/Sales',
    'author': 'drellxor',
    'depends': [
        'product',
        'stock',
        'brochures',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/data_source_data.xml',
        'views/data_source_views.xml',
        'views/product_make_views.xml',
        'views/product_application_views.xml',
        'views/product_template_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'auto_install': False,
}
