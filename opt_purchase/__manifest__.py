# -*- coding: utf-8 -*-
{
    "name": "OPT: Purchase-related customizations",
    "summary": """OPT: Purchase-related customizations""",
    "description": """
2166503
""",
    "author": "Odoo Inc",
    "license": "OEEL-1",
    "website": "http://www.odoo.com",
    "category": "Custom Development",
    "version": "0.1",
    "depends": ["purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/purchase_order_views.xml",
        "views/purchase_level_views.xml",
        "views/purchase_proxy_views.xml"
    ]
}
