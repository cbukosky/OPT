# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PurchaseAccountGroup(models.Model):
    _name = 'purchase.account.group'
    _description = 'Purchase Account Group'

    name = fields.Char('Account Group', required=True)
    active =fields.Boolean('Active', default=True)
    
    # _sql_constraints = [
    #     ('name_uniq', 'unique (name)', 'Account Group(name) must be unique!')
    # ]


class PurchaseChargeCode(models.Model):
    _name = 'purchase.charge.code'
    _description = 'Purchase Charge Code'

    name = fields.Char('Charge Code', required=True)
    project_opt = fields.Char('Project ID')
    active = fields.Boolean('Active')

    # _sql_constraints = [
    #     ('name_uniq', 'unique (name)', 'Charge Code(name) must be unique!')
    # ]


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

    def _compute_can_edit_approval(self):
        for approval in self:
            approval.can_edit_approval = not approval.user_id or approval.user_id == self.env.user


class PurchaseProxy(models.Model):
    _name = 'purchase.proxy'
    _description = 'Purchase Proxy'

    approver_id = fields.Many2one('res.users', ondelete='set null', string='Approver')
    proxy_id = fields.Many2one('res.users', delete='set null', string='Proxy')
    active = fields.Boolean('Active')

    
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    charge_code_id = fields.Many2one('purchase.charge.code', ondelete='restrict', string='Charge Code')
    approval_ids = fields.One2many('purchase.approval', 'order_id', string='Approvals', store=True, readonly=True, copy=False)  # use a wizard to let user update
    approval_count = fields.Integer('Approval Count', readonly=True, compute='_compute_approval_count')
    approved = fields.Boolean('Approved', readonly=True, compute='_compute_approved')
    show_action_approve = fields.Boolean('Show Approve Button', readonly=True, compute='_compute_show_action_approve')

    proxy_ids = fields.Many2many('purchase.proxy', string='Proxies', readonly=True, copy=False)


    def _compute_approved(self):
        for order in self:
            order.approved = order.approval_ids and all(order.approval_ids.mapped('approved')) or False

    def _compute_approval_count(self):
        for order in self:
            order.approval_count = len(order.approval_ids)
            
    def _compute_show_action_approve(self):
        for order in self:
            order.show_action_approve = False
            if order.state == 'draft' and self.env.user in order.approval_ids.mapped('user_id'):
                order.show_action_approve = True

    def _get_approval_users(self):
        self.ensure_one()
        user_ids = self.env['res.users']
        if self.charge_code_id:
            level_ids = self.env['purchase.level'].search([('name', '=', self.charge_code_id.project_opt), ('approval_min', '<=', self.amount_total)])
            user_ids = level_ids.mapped('user_id')
        return user_ids

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

                # send approval email to approvers
                template = self.env.ref('opt_purchase.mail_template_po_approval')
                partners = diff_user_ids.mapped('partner_id')
                if partners:
                    template.send_mail(order.id, force_send=True, email_values={'recipient_ids': [(4, p.id) for p in partners]})

            proxy_ids = order.env['purchase.proxy'].search([('approver_id', 'in', order.approval_ids.mapped('user_id').ids)])  # it should exclude non-active records by default
            new_proxy_ids = set(proxy_ids) - set(order.proxy_ids)
            order.write({'proxy_ids': [(6, 0, proxy_ids.ids)]})
            proxy_template = self.env.ref('opt_purchase.mail_template_po_notification')
            proxy_partners = [p.approver_id.partner_id for p in new_proxy_ids]
            if proxy_partners:
                proxy_template.send_mail(order.id, force_send=True, email_values={'recipient_ids': [(4, p.id) for p in proxy_partners]})
        
    def action_approve(self):
        self.ensure_one()
        action_id = self.env.ref("opt_purchase.action_purchase_approval_tree")
        action_data = action_id.read()[0]
        
        action_data.update({
            'domain': [('order_id', '=', self.id)],
            'context': {'default_order_id': self.id},
            'target': 'new'
        })
        
        return action_data

    @api.multi
    def button_confirm(self):
        self.action_compute_approval_ids()
        invalid_orders = self.filtered(lambda o: not o.approved) 
        if invalid_orders:
            raise ValidationError(_('{} are not approved by all approvers, please contact the Manager.'.format([o.name for o in invalid_orders])))
        res = super(PurchaseOrder, self).button_confirm()
        return res

    
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    account_group_id = fields.Many2one('purchase.account.group', ondelete='restrict', string='Account Group')
