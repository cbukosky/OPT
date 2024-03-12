# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    'name': "BOM Structure & Cost Report in Excel | BOM Structure Report In Excel | BOM Cost Report In Excel",
    'author': 'Softhealer Technologies',
    'website': 'https://www.softhealer.com',
    "support": "support@softhealer.com",
    'category': 'Manufacturing',
    'version': '15.0.1',
    "summary": "Export BOM Structure & Cost Report Export BOM Structure Report Export Cost Report Bill Of Material Structure Report Bill Of Material Cost Report Bill Of Materials Structure Report Bill Of Materials Cost Report In XLS BOM Structure Report In XLS Odoo",
    "description": """This module helps to generate and print BOM structure and cost report in excel format. Report is generates with products & BOM details.""",
    "depends": ['mrp'],

    "data": [
        'security/ir.model.access.csv',
        'views/bom_structure_excel.xml',
        'views/report_xlsx_view.xml',
    ],

    "images": ["static/description/background.png", ],
    "installable": True,
    "auto_install": False,
    "application": True,
    "price": 40,
    "license": "OPL-1",
    "currency": "EUR"
}
