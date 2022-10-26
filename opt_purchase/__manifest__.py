{
    "name": "OPT: Purchase-related customizations",
    "summary": """OPT: Purchase-related customizations""",
    "description": """
        Task: 2166503, 2499185
        - Add calculated field PO balance
    """,
    "author": "Odoo Inc",
    "license": "OPL-1",
    "website": "http://www.odoo.com",
    "category": "Custom Development",
    "version": "1.1",
    "depends": ['account', 'purchase'],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "data/ir_actions_server.xml",
        "data/ir_sequence.xml",
        "data/expense_class_data.xml",
        "views/expense_class_views.xml",
        "views/purchase_order_views.xml",
        "views/purchase_level_views.xml",
        "views/purchase_proxy_views.xml",
        "views/purchase_charge_code_views.xml",
        "views/account_move_views.xml",
        "wizard/wizard_import_helper.xml",
        "wizard/account_move_state_views.xml",
    ]
}
