# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class WizardImportHelper(models.TransientModel):
    _name = 'wizard.import.helper'
    _description = 'Import Helper Wizard'

    name = fields.Selection([('purchase.charge.code', 'Purchase Charge Code'), ('purchase.account.group', 'Account Group')], string='Model')
    file = fields.Binary(string='Import File')
    project_id = fields.Char(string='Project ID')

    currency_id = fields.Many2one(comodel_name='res.currency', default=lambda self: self._get_currency())

    user = fields.Many2one(comodel_name='res.users', string='User')
    amount = fields.Char(string='Amount')

    user0 = fields.Many2one(comodel_name='res.users')
    amount0 = fields.Monetary(default=0)

    user1 = fields.Many2one(comodel_name='res.users')
    amount1 = fields.Monetary(default=500)

    user2 = fields.Many2one(comodel_name='res.users')
    amount2 = fields.Monetary(default=1000)

    user3 = fields.Many2one(comodel_name='res.users')
    amount3 = fields.Monetary(default=5000)

    user4 = fields.Many2one(comodel_name='res.users')
    amount4 = fields.Monetary(default=10000)

    user5 = fields.Many2one(comodel_name='res.users')
    amount5 = fields.Monetary(default=50000)

    def _get_currency(self):
        user = self.env['res.users'].browse(self.env.context['uid'])
        return user.company_id.currency_id

    # A helper function to set the criteria of what is considered a duplicate
    def _get_existing_record_filtering_domain(self, record):
        if self.name == 'purchase.charge.code':
            return lambda r: r.id != record.id and r.name == record.name and r.project_opt == record.project_opt
        elif self.name == 'purchase.account.group':
            return lambda r: r.id != record.id and r.name == record.name
        return lambda r: r

    def do_import(self, model_name, decoded_file, options):
        import_id = self.env['base_import.import'].create({
                'res_model': model_name,
                'file': decoded_file,
                'file_type': 'text/csv'
            })
        file_length, rows = import_id._read_file(options)
        if options.get('has_headers') and rows:
            headers = rows.pop(0)
            header_types = import_id._extract_headers_types(headers, rows, options)
        else:
            header_types, headers = {}, []

        valid_fields = import_id.get_fields_tree(model_name)
        matches = import_id._get_mapping_suggestions(headers, header_types, valid_fields)

        matches = {
            header_key[0]: suggestion['field_path']
            for header_key, suggestion in matches.items()
            if suggestion
        }
        recognized_fields = [(matches[i] and matches[i][0]) or False for i in range(len(matches))]
        import_id.sudo().execute_import(recognized_fields, headers, options)
        if not len(matches):
            raise ValidationError(_('Cannot create/find {} records from the uploaded file.\n'
                                    'Make sure the headers of your file match the technical or functional field names on model {}.\n\n'
                                    'Input Header: {}\n'
                                    'Mapped Header: {}'.format(model_name, model_name, headers, recognized_fields)))

    def action_set_purchase_levels(self):
        """
        Wizard method to assign purchase levels (users and amounts) to a newly imported Project ID.
        The context contains a list of Project IDs. This function will be called once for each Project ID in the
        list and each iteration will pop the first element from the list, decreasing its size by one each time until empty.
        """
        self.ensure_one()

        new_project_ids = self._context.get('new_project_ids')

        # Case when all the project IDs have been assigned purchase levels
        if not new_project_ids or new_project_ids == '':
            return {'type': 'ir.actions.act_window_close'}

        project_id = new_project_ids.pop(0)
        # Unlink previous purchase levels for the current project ID
        old_records = self.env['purchase.level'].search([('name', '=', project_id)]).unlink()
        _logger.info('Setting purchase levels for Project ID: %s' % project_id)

        # Loop through all the user fields in the wizard view
        for i in range(6):
            user = getattr(self, 'user%s' % i)
            amount = getattr(self, 'amount%s' % i)

            if user:
                purchase_level_model = self.env['purchase.level']
                if not purchase_level_model.search([('name', '=', project_id), ('user_id', '=', user.id)]):
                    purchase_level_model.create({
                        'name': project_id,
                        'user_id': user.id,
                        'approval_min': amount
                    })

        if new_project_ids:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Set Purchase Levels',
                'view_mode': 'form',
                'res_model': 'wizard.import.helper',
                'views': [(self.env.ref('opt_purchase.wizard_purchase_levels').id, 'form')],
                'target': 'new',
                'context': {'new_project_ids': new_project_ids,'default_project_id': new_project_ids[0]},
            }

        return {'type': 'ir.actions.act_window_close'}

    def action_import_records(self):
        self.ensure_one()
        new_project_ids = []
        if self.name and self.file:
            model_name = self.name
            decoded_file = base64.b64decode(self.file)
            options = {'quoting': '"', 'separator': ',', 'has_headers': True}

            existing_records = self.env[model_name].with_context(active_test=False).search([])
            self.do_import(model_name, decoded_file, options)
            new_records = self.env[model_name].with_context(active_test=False).search([]) - existing_records

            # Remove duplicates by removing old records that match the new ones according to our duplicate domain
            corrected_record_lst = []
            to_unlink = self.env[model_name]
            charge_code_project_ids = self.env['purchase.charge.code'].search([('active', '=', True)]).mapped('project_opt')
            purchase_level_project_ids = self.env['purchase.level'].search([]).mapped('name')

            for i in range(len(new_records)):
                record = new_records[i]
                existing_record_id = existing_records.filtered(self._get_existing_record_filtering_domain(record))
                if existing_record_id:
                    to_unlink |= record
                    record = existing_record_id[0]

                # If a new Project ID is found during import, the process will interrupt and a new dialog will
                # open that will require the user to select approving users and approval values for the new Project ID
                # A Product ID is considered new if it is not assigned to any charge code or if it is assigned to a charge Code
                # but it does not have any purchase levels associated with it
                if self.name == 'purchase.charge.code':
                    pid = record.project_opt
                    if pid not in new_project_ids and (pid not in charge_code_project_ids or (pid in charge_code_project_ids and pid not in purchase_level_project_ids)):
                        _logger.info("Importing Project ID: %s" % pid)
                        new_project_ids.append(pid)

                record.sudo().write({
                    'active': True,
                })
                corrected_record_lst.append(record.id)
            to_unlink.sudo().unlink()

            self.env[model_name].sudo().search([('id', 'not in', corrected_record_lst)]).write({'active': False})

        if new_project_ids:
            # Return wizard for setting purchase Levels for the new Project IDs

            self.project_id = new_project_ids[0]
            return {
                'type': 'ir.actions.act_window',
                'name': 'Set Purchase Levels',
                'view_mode': 'form',
                'res_model': 'wizard.import.helper',
                'views': [(self.env.ref('opt_purchase.wizard_purchase_levels').id, 'form')],
                'target': 'new',
                'context': {'new_project_ids': new_project_ids, 'default_project_id': self.project_id},
            }

        return {'type': 'ir.actions.act_window_close'}
