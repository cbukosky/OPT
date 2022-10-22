from odoo import api, fields, models, _


class ExpenseClass(models.Model):
    _name = 'expense.class'
    _description = 'Expense Class'

    name = fields.Char('Name', required=True)
