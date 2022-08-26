# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    charge_code_id = fields.Many2one('purchase.charge.code', ondelete='restrict', string='Charge Code', required=True)
    approval_ids = fields.One2many('purchase.approval', 'order_id', string='Approvals', store=True, readonly=True, copy=False)  # use a wizard to let user update
    approval_count = fields.Integer('Approval Count', readonly=True, compute='_compute_approval_count')
    approved = fields.Boolean('Approved', readonly=True, compute='_compute_approved', store=True)
    show_action_approve = fields.Boolean('Show Approve Button', readonly=True, compute='_compute_show_action_approve')
    show_action_confirm = fields.Boolean('Show Confirm Button', readonly=True, compute='_compute_show_action_confirm')
    ap_gl_account = fields.Many2one('apgl.account', string='AP GL Account')
    proxy_ids = fields.Many2many('purchase.proxy', string='Proxies', readonly=True, copy=False)
    expense_class = fields.Many2one('expense.class')
    po_balance = fields.Float(string='PO Balance', compute='_compute_po_balance')
    invoice_status = fields.Selection(selection_add=[
        ('closed', 'Closed'),
    ], string='Billing Status', compute='_get_invoiced', store=True, readonly=True, copy=False, default='no')

    @api.depends('approval_ids', 'approval_ids.approved')
    def _compute_approved(self):
        for order in self:
            order.approved = order.approval_ids and all(order.approval_ids.mapped('approved')) or False

    @api.depends('amount_total', 'order_line.qty_received', 'order_line.price_unit')
    def _compute_po_balance(self):
        for order in self:
            total = order.amount_total
            received_price = 0
            for line in order.order_line:
                received_price += line.qty_received * line.price_unit
            order.po_balance = total - received_price

    @api.depends('state', 'order_line.qty_to_invoice')
    def _get_invoiced(self):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for order in self:
            if all(float_compare(line.product_qty, line.qty_received, precision_digits=precision) == 0 and
                   float_compare(line.qty_received, line.qty_invoiced, precision_digits=precision) == 0 for line in order.order_line):
                self.invoice_status = 'closed'
            else:
                super(PurchaseOrder, order)._get_invoiced()

    def _compute_approval_count(self):
        for order in self:
            order.approval_count = len(order.approval_ids)

    def _compute_show_action_confirm(self):
        for order in self:
            order.show_action_confirm = False
            if not order.approval_ids or order.approved:
                order.show_action_confirm = True

    def _compute_show_action_approve(self):
        for order in self:
            order.show_action_approve = False
            if order.state in ('draft', 'sent') and (self.env.user in order.approval_ids.mapped('user_id') or self.env.user in order.proxy_ids.mapped('proxy_id')):
                order.show_action_approve = True

    def _get_approval_users(self):
        self.ensure_one()
        user_ids = self.env['res.users']
        if self.charge_code_id:
            level_ids = self.env['purchase.level'].search([('name', '=', self.charge_code_id.project_opt), ('approval_min', '<=', self.amount_total)])
            user_ids = level_ids.mapped('user_id')
        return user_ids

    def notify_approvers(self):
        for order in self:
            # From the partners that have not approved yet, select the ones with the lower hierarchy
            # of approval levels. If there are multiple partners for a certain amount, return them all
            approved = order.approval_ids.filtered(lambda a: a.approved).mapped('user_id')
            level_ids = self.env['purchase.level'].search([('name', '=', order.charge_code_id.project_opt),
                                                           ('approval_min', '<=', self.amount_total),
                                                           ('user_id', 'not in', approved.ids)])
            users_by_level = {}
            for level in level_ids:
                amount = level.approval_min
                if users_by_level.get(amount):
                    users_by_level[amount] += level.mapped('user_id')
                else:
                    users_by_level[amount] = level.mapped('user_id')
            users = users_by_level[min(users_by_level.keys())] if users_by_level else []

            # Make sure that we have not already sent the notification. The approval re-computation can be
            # done multiple times so we do not want to send the notification more than once
            all_messages = self.env['mail.message'].search([('model', '=', 'purchase.order'),
                                                            ('res_id', '=', order.id),
                                                            ('subject', 'ilike', 'approval')])
            recipients = self.env['res.partner']
            for user in users:
                if not all_messages.filtered(lambda m: user.mapped('partner_id') in m.partner_ids):
                    recipients += user.mapped('partner_id')

            # Send notification
            template = self.env.ref('opt_purchase.mail_template_po_approval')
            for recipient in recipients:
                email_values = {'recipient': recipient.name}
                template.sudo().with_context(email_values).send_mail(order.id, force_send=True,
                                   email_values={'recipient_ids': [(4, p.id) for p in recipients]})

            # Notify respective proxies
            if users:
                proxy_ids = order.env['purchase.proxy'].search([('approver_id', 'in', users.ids)])
                proxy_template = self.env.ref('opt_purchase.mail_template_po_notification')
                proxy_partners = [p.proxy_id.partner_id for p in proxy_ids]
                for proxy in proxy_partners:
                    email_values = {'proxy': proxy.name}
                    proxy_template.sudo().with_context(email_values).send_mail(order.id, force_send=True, email_values={'recipient_ids': [(4, p.id) for p in proxy_partners]})

    def action_compute_approval_ids(self):
        for order in self.filtered(lambda o: o.state in ['draft', 'sent']):
            existing_user_ids = order.approval_ids.mapped('user_id')
            new_user_ids = order._get_approval_users()
            order.approval_ids.filtered(lambda approval: approval.user_id not in new_user_ids).unlink()
            diff_user_ids = new_user_ids - existing_user_ids
            new_approvals = self.env['purchase.approval'].create([{'user_id': user.id, 'approved': False} for user in diff_user_ids])
            order.write({'approval_ids': [(4, id, 0) for id in new_approvals.ids]})

            proxy_ids = order.env['purchase.proxy'].search([('approver_id', 'in', order.approval_ids.mapped('user_id').ids)])
            order.write({'proxy_ids': [(6, 0, proxy_ids.ids)]})

            # send approval email to approvers and proxies
            order.notify_approvers()

    def action_approve(self):
        self.ensure_one()
        return {
            'name': _('Purchase Approval'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'purchase.approval',
            'target': 'new',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
        }

    def button_confirm(self):
        self.action_compute_approval_ids()
        inactive_charge_codes = self.filtered(lambda o: not o.charge_code_id.active)
        if inactive_charge_codes:
            raise ValidationError(_('{} Charge code is inactive, please contact the Manager.'.format([o.name for o in inactive_charge_codes])))

        inactive_account_groups = self.filtered(lambda o: not all(o.order_line.mapped('account_group_id.active')))
        if inactive_account_groups:
            raise ValidationError(_('{} Account Group in Purchase Order line is inactive, please contact the Manager.'.format([o.name for o in inactive_account_groups])))

        not_approved_orders = self.filtered(lambda o: o.approval_ids and not o.approved)
        if not_approved_orders:
            raise ValidationError(_('{} are not approved by all approvers, please contact the Manager.'.format([o.name for o in not_approved_orders])))

        res = super(PurchaseOrder, self).button_confirm()
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    account_group_id = fields.Many2one('purchase.account.group', ondelete='restrict', string='Account Group', required=True)
