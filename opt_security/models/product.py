from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    message_main_attachment_id = fields.Many2one(
        domain=[("specified_on_product", "=", True)]
    )
