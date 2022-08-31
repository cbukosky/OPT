# -*- encoding: utf8 -*-

from odoo.addons.base.maintenance.migrations import util


def migrate(cr, version):
    cr.execute("ALTER TABLE purchase_order_line ALTER COLUMN charge_code_id DROP NOT NULL")
    cr.execute("ALTER TABLE purchase_order_line ALTER COLUMN account_group_id DROP NOT NULL")
