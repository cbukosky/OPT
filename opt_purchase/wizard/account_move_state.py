# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import UserError

class AccountInvoiceApprove(models.TransientModel):
    """
    This wizard will confirm the all the selected Ready for Approval invoices.
    Approve is the same as Confirm but has to be done by the Account Manager
    """

    _name = "account.invoice.approve"
    _description = "Approve the selected invoices"


    def invoice_approve(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['account.invoice'].browse(active_ids):
            if record.state != 'to_approve':
                raise UserError(_("Selected invoice(s) cannot be confirmed as they are not in 'Ready for Approval' state."))
            record.action_post()
        return {'type': 'ir.actions.act_window_close'}
