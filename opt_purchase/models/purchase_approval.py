# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from pytz import timezone

from odoo import api, fields, models, _

class PurchaseAccountGroup(models.Model):
    _name = 'purchase.account.group'
    _description = 'Purchase Account Group'

    name = fields.Char('Account Group', required=True)
    active = fields.Boolean('Active', default=True)

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

class PurchaseProxy(models.Model):
    _name = 'purchase.proxy'
    _description = 'Purchase Proxy'

    approver_id = fields.Many2one('res.users', ondelete='set null', string='Approver')
    proxy_id = fields.Many2one('res.users', delete='set null', string='Proxy')
    active = fields.Boolean('Active')

class PurchaseApproval(models.Model):
    _name = 'purchase.approval'
    _description = 'Purchase Approval'

    order_id = fields.Many2one('purchase.order', ondelete='cascade', string='Purchase Order')
    user_id = fields.Many2one('res.users', ondelete='set null', string='Approver')
    approved = fields.Boolean('Approved')
    can_edit_approval = fields.Boolean('Approval can be edited by current user', readonly=True, compute='_compute_can_edit_approval')

    ready_approval = fields.Boolean('Ready to be approved by this approver', readonly=True, compute='_compute_can_approve')
    # date_approved = fields.Datetime(string='Date', readonly=True)

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
                                                datetime.now(tz).strftime('%m/%d/%Y %H:%M')
                ))

        # Notify next set of users requesting their approval
        if vals.get('approved'):
            self[0].order_id.notify_approvers()


    def _compute_can_edit_approval(self):
        # The current user can approve if he is the approver in the approvals table or
        # if he is a proxy for a user that is in the approvals table
        proxy_model = self.env['purchase.proxy']

        for approval in self:
            approval.can_edit_approval = not approval.user_id or \
                                         approval.user_id == self.env.user or \
                                         proxy_model.search([('proxy_id', '=', self.env.user.id)]).mapped('approver_id') in approval.mapped('user_id')

