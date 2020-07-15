# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import pycompat
import io, base64, random, string 


def _csv_write_rows(rows):
    f = io.BytesIO()
    writer = pycompat.csv_writer(f, delimiter=',', quotechar='"', quoting=2, dialect='excel')
    rows_length = len(rows)
    for i, row in enumerate(rows):
        writer.writerow(row)

    fvalue = f.getvalue()
    f.close()
    return fvalue


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    project_code = fields.Char('Project Code')
    
    @api.multi
    def generate_export_data(self, export_sequence):
        header = ['Export #', 'Bill #', 'PO #', 'Project Code', 'Account Code', 'Vendor Name', 'Total']
        new_export = self.env['account.invoice.line'].search([
            ('invoice_id', 'in', self.ids),
            ('export_sequence', 'in', ('', False))
        ])
        new_export.write({'export_sequence': export_sequence})
        # not sure if customer wants to export already exported lines or not
        # so for now, only export new lines
        content = []
        for bill in self:  # since they want to group by bill
            bill_group = {}
            for line in bill.invoice_line_ids.filtered(lambda l: l.export_sequence == export_sequence):
                key = (line.export_sequence, line.invoice_id.number, line.purchase_id.name, line.invoice_id.project_code, line.charge_code_id.name, line.invoice_id.partner_id.name)
                if not bill_group.get(key):
                    bill_group[key] = 0.0
                bill_group[key] += line.price_total  # assuming they are using the same currency here, might need to revise if they want multicurrency
            content.extend([list(k) + [bill_group.get(k)] for k in bill_group.keys()])
        
        data = [header] + content
        return _csv_write_rows(data)
    
    @api.multi
    def action_export(self):
        self = self.env['account.invoice'].search([
            ('id', 'in', self.ids),
            ('state', 'not in', ('draft', 'cancel')),
            ('type', '=', 'in_invoice'),
        ])

        if not self:
            return {}

        export_sequence = self.env['ir.sequence'].next_by_code('export.vendor.bill')
        if not export_sequence:
            raise ValidationError(_('Please define sequence for export vendor bill'))
        
        Attachment = self.env['ir.attachment'].sudo()
        attachment_name = 'Vendor_Bill_Batch_{}.csv'.format(export_sequence)
        data = self.generate_export_data(export_sequence)
        
        attachment_vals = {
            'name': attachment_name,
            'datas': base64.encodestring(data),
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

    charge_code_id = fields.Many2one('purchase.charge.code', ondelete='restrict', string='Charge Code')
    # account_group_id = fields.Many2one('purchase.account.group', ondelete='restrict', string='Account Group')

    export_sequence = fields.Char('Export #', readonly=True, copy=False)

