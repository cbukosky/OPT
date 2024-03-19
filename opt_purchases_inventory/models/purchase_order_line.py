from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.line",
        string="Analytic Account Line"
    )

    def _prepare_stock_moves(self, picking):
        vals = super()._prepare_stock_moves(picking)
        for rec in vals:
            rec['analytic_account_line_id'] = self.analytic_account_id.id
        return vals

