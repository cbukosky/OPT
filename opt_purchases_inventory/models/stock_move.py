from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        stock_lines = super().create(vals_list)
        for rec in stock_lines:
            if rec.purchase_line_id and not rec.analytic_account_line_id:
                rec.analytic_account_line_id = rec.purchase_line_id.analytic_account_id
            elif rec.origin and not rec.purchase_line_id:
                purchase_line = self.env['purchase.order'].search([('name', '=', rec.origin)]).order_line
                for po_line in purchase_line:
                    if po_line.product_id == rec.product_id:
                        rec.write({
                            'analytic_account_line_id': po_line.analytic_account_id
                        })
        return stock_lines
