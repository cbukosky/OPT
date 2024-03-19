from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_analytic_account = fields.Boolean()

