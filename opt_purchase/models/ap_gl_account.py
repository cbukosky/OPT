from odoo import api, fields, models, _


class APGLAccount(models.Model):
    _name = 'apgl.account'
    _description = 'AP GL Account'

    name = fields.Char('Name', required=True)
