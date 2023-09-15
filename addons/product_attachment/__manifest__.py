{
    'name': 'Product attachment',
    'version': '1.0',
    'description': "Adds attachments to product template",
    'category': 'Sales/Sales',
    'author': 'drellxor',
    'depends': [
        'simplify_odoo'
    ],
    'data': [
        'security/ir.model.access.csv',

        'data/ir_config_parameter.xml',

        'views/product_attachment.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'auto_install': False
}
