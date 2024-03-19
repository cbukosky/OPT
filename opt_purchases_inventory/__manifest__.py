# -*- coding: utf-8 -*-
{
    'name': "OPT Purchases Inventory",
    'summary': """OPT Purchases Inventory""",
    'description': """User Story 04""",
    'author': 'Polaris Integrators',
    'website': 'https://polarisintegrators.com/',
    'category': 'purchase',
    'version': '15.0.1.2.0',
    'depends': ['purchase_stock', 'stock'],
    'data': [
        'views/stock_picking_views.xml',
        'views/purchase_order_line_views.xml',
    ],
    "license": "AGPL-3",
    "installable": True,
    "application": True,
}
