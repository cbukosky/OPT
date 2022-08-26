# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import io, base64

from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools import email_re, email_split, email_escape_char, float_is_zero, float_compare, \
    pycompat, date_utils


def _csv_write_rows(rows):
    f = io.BytesIO()
    writer = pycompat.csv_writer(f, delimiter=',', quotechar='"', quoting=2, dialect='excel')
    rows_length = len(rows)
    for i, row in enumerate(rows):
        writer.writerow(row)

    fvalue = f.getvalue()
    f.close()
    return fvalue


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('invoice_line_ids.export_sequence')
    def _compute_exported(self):
        for record in self:
            if any(record.invoice_line_ids.mapped('export_sequence')):
                record.exported = True
            else:
                record.exported = False

    def _get_states(self):
        return [
                ('draft', 'Draft'),
                ('to_approve', 'Ready for Approval'),
                ('posted', 'Approved'),
                ('in_payment', 'In Payment'),
                ('paid', 'Paid'),
                ('cancel', 'Cancelled')
        ]

    charge_code_id = fields.Many2one('purchase.charge.code', string='Charge Code', related='purchase_id.charge_code_id', store=True)
    exported = fields.Boolean(string='Exported to QB', compute='_compute_exported', readonly=True, store=True)
    state = fields.Selection(_get_states, string='Status', index=True, readonly=True, default='draft',
    tracking=True, copy=False,
    help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
         " * The 'Ready for Approval' status is used when user creates invoice, an invoice number is generated but the Accounting Manager still needs to approve the invoice.\n"
         " * The 'Approved' status is used when the invoice needs to paid by the customer.\n"
         " * The 'In Payment' status is used when payments have been registered for the entirety of the invoice in a journal configured to post entries at bank reconciliation only, and some of them haven't been reconciled with a bank statement line yet.\n"
         " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
         " * The 'Cancelled' status is used when user cancel invoice.",
    ondelete=None)

    # @api.model
    # def _unlink_confirm_invoice_action(self):
    #     action = self.env.ref('account.action_account_invoice_confirm', raise_if_not_found=False)
    #     if action:
    #         action.unlink()

    def generate_export_data(self, export_sequence):
        header = ['Quickbook Name:',
                  'Export #',
                  'Bill No',
                  'Vendor',
                  'Date',
                  'Due Date',
                  'AP Account',
                  'Memo',
                  'Expense Class',
                  'Expense Account',
                  'Expense Customer',
                  'Expense Amount',
                  'Expense Memo',
                  ]

        # Get the bill lines that have never been exported before. See comment below
        new_export = self.env['account.move.line'].search([
            ('move_id', 'in', self.ids),
            ('export_sequence', 'in', ('', False))
        ])
        new_export.write({'export_sequence': export_sequence})

        # not sure if customer wants to export already exported lines or not
        # so for now, only export new lines

        content = []
        for bill in self:  # since they want to group by bill
            bill_group = {}
            for line in bill.invoice_line_ids.filtered(lambda l: l.export_sequence == export_sequence):
                key = (line.export_sequence or '',
                       line.move_id.ref or line.move_id.name or '',
                       line.move_id.partner_id.name or '',
                       line.move_id.invoice_date.strftime("%m/%d/%Y") or '',
                       line.move_id.invoice_date_due.strftime("%m/%d/%Y") or '',
                       line.ap_gl_accounapt.name or '',
                       line.purchase_id.name or '',
                       line.purchase_id.expense_class.name or '',
                       line.account_group.name or '',
                       line.move_id.charge_code_id.name or ''
                       )
                if not bill_group.get(key):
                    line_data = [0.0, line.name]
                else:
                    line_data[1] = 'Various Parts'  # If there are more that one line we want to have a fixed description

                line_data[0] += line.price_total  # assuming they are using the same currency here, might need to revise if they want multicurrency
                bill_group[key] = line_data
            content.extend([[""] + list(k) + list(bill_group.get(k)) for k in bill_group.keys()])

        data = [header] + content
        return _csv_write_rows(data)

    def action_export(self):
        if self.filtered(lambda bill: bill.move_type != 'in_invoice'):
            raise ValidationError('You can only export Vendor Bills.')
        if self.filtered(lambda bill: bill.state != 'posted'):
            raise ValidationError('The bill must in the approved state in order to export it.')

        self = self.env['account.move'].search([
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
            'datas': base64.encodebytes(data),
            'res_model': 'account.move',
        }

        Attachment.search([('name', '=', attachment_name)]).unlink()

        attachment = Attachment.create(attachment_vals)

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment.id),
            'target': 'self'
        }

    def action_invoice_to_approve(self):
        # Method similar to action_post but before approval stage
        if self.filtered(lambda inv: inv.move_type == 'in_invoice' and inv.state != 'draft'):
            raise UserError(_("Invoice must be in draft state in order to request approval of the Accounting Manager."))
        return self.write({'state': 'to_approve'})

    def action_post(self):
        to_post_invoices = self.filtered(lambda inv: inv.move_type == 'in_invoice' and inv.state != 'posted')
        if to_post_invoices.filtered(lambda inv: inv.state != 'to_approve'):
            raise UserError(_("Invoice must be in Ready to Approve state in order to validate it."))
        return super(AccountMove, self).action_post()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    account_group = fields.Many2one('purchase.account.group', string='Account Group', compute='_compute_account_group', inverse='_inverse_account_group', store=True)
    ap_gl_account = fields.Many2one('apgl.account', string='AP GL Account', related='purchase_line_id.order_id.ap_gl_account', store=True)
    export_sequence = fields.Char('Export #', readonly=True, copy=False)

    @api.depends('purchase_line_id')
    def _compute_account_group(self):
        for record in self:
            record.account_group = record.purchase_line_id.account_group_id.id

    def _inverse_account_group(self):
        pass
