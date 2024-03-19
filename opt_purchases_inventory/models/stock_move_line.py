from odoo import fields, models, api


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.line",
        related="move_id.analytic_account_line_id",
        string="Analytic Account Line",
        store=True,
        readonly=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        stock_lines = super().create(vals_list)
        for stock_line in stock_lines:
            if stock_line.move_id:
                for move_id in stock_line.move_id.filtered(
                        lambda move: move.product_id == stock_line.product_id):
                    stock_line.write({
                        'analytic_account_id': move_id.analytic_account_line_id.id
                    })
                    move_id.picking_id.is_analytic_account = True
        return stock_lines

