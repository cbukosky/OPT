# -*- encoding: utf8 -*-


def migrate(cr, version):
    cr.execute("ALTER TABLE purchase_order_line ALTER COLUMN charge_code_id DROP NOT NULL")
    cr.execute("ALTER TABLE purchase_order_line ALTER COLUMN account_group_id DROP NOT NULL")
