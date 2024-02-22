# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Techerp Solutions                                                  #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################
{
    'name': 'Purchase Order Line Quantity, Price History',
    'version': '15.0.1.0',
    'summary': '''
This Module Adds tab for Price and Quantity change History, Purchase Line Amendment
    ''',
    'category': 'Purchases',
    'description': """
This Module Adds tab for Quantity and Quantity change History, Purchase Line Amendment
    """,
    'author': 'Techerp Solutions',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_line_history_view.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'qweb': [],
    'price': 11.00,
    'currency': 'USD',
}
