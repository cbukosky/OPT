# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from pytz import timezone

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class PurchaseAccountGroup(models.Model):
    _name = 'purchase.account.group'
    _description = 'Purchase Account Group'

    name = fields.Char('Account Group', required=True)
    active =fields.Boolean('Active', default=True)

class PurchaseChargeCode(models.Model):
    _name = 'purchase.charge.code'
    _description = 'Purchase Charge Code'

    name = fields.Char('Charge Code', required=True)
    project_opt = fields.Char('Project ID')
    active = fields.Boolean('Active')

class PurchaseLevel(models.Model):
    _name = 'purchase.level'
    _description = 'purchase.level'

    name = fields.Char('Project ID')
    user_id = fields.Many2one('res.users', ondelete='set null', string='User')
    approval_min = fields.Float('Approval Min')


class PurchaseApproval(models.Model):
    _name = 'purchase.approval'
    _description = 'Purchase Approval'

    order_id = fields.Many2one('purchase.order', ondelete='cascade', string='Purchase Order')
    user_id = fields.Many2one('res.users', ondelete='set null', string='Approver')
    approved = fields.Boolean('Approved')
    can_edit_approval = fields.Boolean('Approval can be edited by current user', readonly=True, compute='_compute_can_edit_approval')
    ready_approval = fields.Boolean('Ready to be approved by this approver', readonly=True, compute='_compute_can_approve')

    def _compute_can_approve(self):
        # The current user is ready to approve if he or she is the first approver or his/her previous approver has approved

        for approval in self:
            # Get all user_ids that need to approve
            level_ids = self.env['purchase.level'].search(
                    [('name', '=', approval.order_id.charge_code_id.project_opt), ('approval_min', '<=', approval.order_id.amount_total)], order='approval_min asc')
            user_ids = level_ids.mapped('user_id.id')

            # Filter out the current PO approvals that are approved
            approvals_unapproved = self.env['purchase.approval'].search([('approved', '=', False), ('user_id', 'in', user_ids), ('order_id', '=', approval.order_id.id)])

            if not approvals_unapproved:
                approval.ready_approval = False
                continue

            # Sort them according to user_ids
            first_approval = approvals_unapproved.sorted(key=lambda a: user_ids.index(a.user_id.id))[0]
            approval.ready_approval = True if approval == first_approval else False

    def write(self, vals):
        super(PurchaseApproval, self).write(vals)
        for approval in self:
            if approval.approved:
                # Post approval info in the chatter
                tz = timezone('US/Eastern')  # Eastern timezone requested by customer
                approval.order_id.message_post(body='%s approved purchase order %s on %s EST' % (
                                                approval.user_id.name,
                                                approval.order_id.name,
                                                datetime.now(tz).strftime('%m/%d/%Y %H:%M'))
                                                )

                # Notify next set of users requesting their approval
                approval.order_id.notify_approvers()


    def _compute_can_edit_approval(self):
        # The current user can approve if he is the approver in the approvals table or
        # if he is a proxy for a user that is in the approvals table
        proxy_model = self.env['purchase.proxy']

        for approval in self:
            approval.can_edit_approval = not approval.user_id or \
                            approval.user_id == self.env.user or \
                            proxy_model.search([('proxy_id', '=', self.env.user.id)]).mapped('approver_id') in approval.mapped('user_id')


class PurchaseProxy(models.Model):
    _name = 'purchase.proxy'
    _description = 'Purchase Proxy'

    approver_id = fields.Many2one('res.users', ondelete='set null', string='Approver')
    proxy_id = fields.Many2one('res.users', delete='set null', string='Proxy')
    active = fields.Boolean('Active')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    charge_code_id = fields.Many2one('purchase.charge.code', ondelete='restrict', string='Charge Code', required=True)
    approval_ids = fields.One2many('purchase.approval', 'order_id', string='Approvals', store=True, readonly=True, copy=False)  # use a wizard to let user update
    approval_count = fields.Integer('Approval Count', readonly=True, compute='_compute_approval_count')
    approved = fields.Boolean('Approved', readonly=True, compute='_compute_approved', store=True)
    show_action_approve = fields.Boolean('Show Approve Button', readonly=True, compute='_compute_show_action_approve')
    show_action_confirm = fields.Boolean('Show Confirm Button', readonly=True, compute='_compute_show_action_confirm')
    proxy_ids = fields.Many2many('purchase.proxy', string='Proxies', readonly=True, copy=False)

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

    @api.depends('state', 'order_line.qty_invoiced', 'order_line.qty_received', 'order_line.product_qty')
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
            if recipients:
                template.send_mail(order.id, force_send=True,
                                   email_values={'recipient_ids': [(4, p.id) for p in recipients]})

            # Notify respective proxies
            if users:
                proxy_ids = order.env['purchase.proxy'].search([('approver_id', 'in', users.ids)])
                proxy_template = self.env.ref('opt_purchase.mail_template_po_notification')
                proxy_partners = [p.proxy_id.partner_id for p in proxy_ids]
                if proxy_partners:
                    proxy_template.send_mail(order.id, force_send=True, email_values={'recipient_ids': [(4, p.id) for p in proxy_partners]})


    def action_compute_approval_ids(self):
        for order in self.filtered(lambda o: o.state == 'draft'):  # recompute will only get called when the order is draft
            existing_user_ids = order.approval_ids.mapped('user_id')
            new_user_ids = order._get_approval_users()
            if new_user_ids != existing_user_ids:
                to_unlink = self.env['purchase.approval']
                for approval in order.approval_ids:
                    if approval.user_id not in new_user_ids:
                        to_unlink |= approval
                to_unlink.unlink()
                diff_user_ids = new_user_ids - existing_user_ids
                for user in diff_user_ids:
                    new_approval = self.env['purchase.approval'].create({
                        'user_id': user.id,
                        'approved': False
                    })
                    order.approval_ids |= new_approval


            proxy_ids = order.env['purchase.proxy'].search([('approver_id', 'in', order.approval_ids.mapped('user_id').ids)])  # it should exclude non-active records by default
            order.write({'proxy_ids': [(6, 0, proxy_ids.ids)]})

            # send approval email to approvers and proxies
            order.notify_approvers()

    def action_approve(self):
        self.ensure_one()
        action_id = self.env.ref("opt_purchase.action_purchase_approval_tree")
        action_data = action_id.read()[0]
        print(action_data)
        action_data.update({
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
            'target': 'new'
        })

        return action_data

    @api.multi
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
