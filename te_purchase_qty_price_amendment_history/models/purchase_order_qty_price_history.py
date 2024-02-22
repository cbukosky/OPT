# -*- coding: utf-8 -*-
##############################################################################
#                                                                            #
# Part of Techerp Solutions                                                  #
# See LICENSE file for full copyright and licensing details.                 #
#                                                                            #
##############################################################################
from odoo import fields,models,api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta

class PurchaseOrderLineHistory(models.Model):
    _name = "te.purchase.order.line.history"
    _description = "Purchase Order Line History"
    _order = 'id desc'

    change_on_date = fields.Datetime('Date')
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_id = fields.Many2one('uom.uom', string='UOM')
    old_product_qty = fields.Float(string='Qty', digits='Product Unit of Measure')
    new_product_qty = fields.Float(string='Amended Qty', digits='Product Unit of Measure')
    old_price_unit = fields.Float(string='Price', digits='Product Unit of Measure')
    new_price_unit = fields.Float(string='Amended Price', digits='Product Unit of Measure')
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase Line')
    order_id = fields.Many2one('purchase.order', string='Purchase Order')

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    history_line_ids = fields.One2many('te.purchase.order.line.history','order_id',
                                    string='Purchase Line History',
                                    readonly=True)

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def write(self, vals):
        POLineHistory = self.env['te.purchase.order.line.history']
        for line in self:
            if line.state != 'purchase':
                return super(PurchaseOrderLine, self).write(vals)
            if (vals.get('product_qty') or vals.get('price_unit')) or (vals.get('product_qty') and vals.get('price_unit')):
                history_vals = {
                            'purchase_line_id': line.id,
                            'change_on_date': datetime.now() or False,
                            'order_id':line.order_id and line.order_id.id or False,
                            'product_uom_id': line.product_uom and line.product_uom.id or False,
                            'product_id': line.product_id and line.product_id.id or False,
                        }
                if vals.get('product_qty'):
                    history_vals.update({'old_product_qty': line.product_qty or 0.0,
                                         'new_product_qty': vals.get('product_qty') or 0.0})
                else:
                    history_vals.update({'old_product_qty': line.product_qty or 0.0,
                                         'new_product_qty': line.product_qty or 0.0})
                if vals.get('price_unit'):
                    history_vals.update({'old_price_unit': line.price_unit or 0.0,
                                         'new_price_unit': vals.get('price_unit') or 0.0})  
                else:
                    history_vals.update({'old_price_unit': line.price_unit or 0.0,
                                         'new_price_unit': line.price_unit or 0.0})                       
                POLineHistory.create(history_vals)
        res = super(PurchaseOrderLine, self).write(vals)

