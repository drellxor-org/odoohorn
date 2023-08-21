{
    'name': 'Feedback',
    'version': '1.0',
    'description': "Customer feedback / requests",
    'category': 'Sales/Sales',
    'author': 'drellxor',
    'depends': [
        'simplify_odoo',
        'article'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/feedback_views.xml'
    ],
    'installable': True,
    'auto_install': False
}
