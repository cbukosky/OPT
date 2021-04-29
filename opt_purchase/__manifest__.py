# -*- coding: utf-8 -*-
{
    "name": "OPT: Purchase-related customizations",
    "summary": """OPT: Purchase-related customizations""",
    "description": """
        Task: 2166503, 2499185
        - Add calculated field PO balance
    """,
    "author": "Odoo Inc",
    "license": "OEEL-1",
    "website": "http://www.odoo.com",
    "category": "Custom Development",
    "version": "0.1",
    "depends": ["purchase"],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "data/ir_actions_server.xml",
        "data/ir_sequence.xml",
        "views/purchase_order_views.xml",
        "views/purchase_level_views.xml",
        "views/purchase_proxy_views.xml",
        "views/purchase_charge_code_views.xml",
        "views/account_invoice_views.xml",
        "wizard/wizard_import_helper.xml",
        # "wizard/wizard_purchase_levels.xml",
        "wizard/account_invoice_state_views.xml",
    ]
}
