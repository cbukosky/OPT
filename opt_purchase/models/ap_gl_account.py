# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class APGLAccount(models.Model):
    _name = 'apgl.account'
    _description = 'AP GL Account'

    name = fields.Char('Name', required=True)
