{
    'name': 'Order product info',
    'version': '1.0',
    'description': "Calculates popularity based on order lines and introduces to fields",
    'category': 'Sales/Sales',
    'author': 'drellxor',
    'depends': [
        'simplify_odoo'
    ],
    'data': [
        'views/sale_order_views.xml',
        'views/product_views.xml'
    ],
    'installable': True,
    'auto_install': False
}
