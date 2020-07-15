# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
    
class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    charge_code_id = fields.Many2one('purchase.charge.code', ondelete='restrict', string='Charge Code')
    account_group_id = fields.Many2one('purchase.account.group', ondelete='restrict', string='Account Group')

    @api.multi
    def generate_export_data(self):
        return ''
    
    @api.multi
    def action_export(self):
        Attachment = self.env['ir.attachment'].sudo()
        attachment_name = 'vendor_bill.csv'
        data = self.generate_export_data()

        attachment_vals = {
            'name': attachment_name,
            'datas': base64.encodestring(data.encode()),
            'datas_fname': attachment_name,
            'res_model': 'account.invoice',
        }

        Attachment.search([('name', '=', attachment_name)]).unlink()

        attachment = Attachment.create(attachment_vals)
        
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment.id),
            'target': 'self'
        }
    
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    batch_number = fields.Char('Export #', readonly=True)

