# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class WizardImportHelper(models.TransientModel):
    _name = 'wizard.import.helper'
    _description = 'Import Helper Wizard'

    name = fields.Selection([('purchase.charge.code', 'Purchase Charge Code'), ('purchase.level', 'Purchase Level')], string='Model')
    file = fields.Binary(string='Import File')

    # a helper function to set the criteria of what is considered a duplicate
    def _get_existing_record_searching_domain(self, record):
        domain = []
        if self.name == 'purchase.charge.code':
            domain = [
                ('id', '!=', record.id),
                ('name', '=', record.name),
                # ('project_opt', '=', record.project_opt)
            ]
        elif self.name == 'purchase.level':
            domain = [
                ('id', '!=', record.id),
                ('name', '=', record.name),
                ('user_id', '=', record.user_id.id),
                # ('approval_min', '=', record.approval_min)
            ]
        # elif self.name == 'purchase.proxy':
        #     domain = [
        #         ('id', '!=', record.id),
        #         ('approver_id', '=', record.approver_id.id),
        #         ('proxy_id', '=', record.proxy_id.id)
        #     ]
        return domain

    def do_import(self, model_name, decoded_file, options):
        import_id = self.env['base_import.import'].create({
                'res_model': model_name,
                'file': decoded_file,
                'file_type': 'text/csv'
            })
        data_gen = import_id._read_file(options)
        # the first item from data generator is header
        header = next(data_gen)
        valid_fields = import_id.get_fields(model_name)
        parsed_header, matches = import_id._match_headers(iter([header]), valid_fields, options)
        recognized_fields = [(matches[i] and matches[i][0]) or False for i in range(len(parsed_header))]
        result = import_id.do(recognized_fields, parsed_header, options)
        rids = result.get('ids')
        if not rids:
            raise ValidationError(_('Cannot create/find {} records from the uploaded file.\n'
                                    'Make sure the headers of your file match the technical or functional field names on model {}.\n\n'
                                    'Input Header: {}\n'
                                    'Mapped Header: {}\n'
                                    'Error Message: {}'.format(model_name, model_name, parsed_header, recognized_fields,
                                                               result.get('messages'))))
        return rids

    def action_import_records(self):
        self.ensure_one()
        if self.name and self.file:
            model_name = self.name
            decoded_file = base64.b64decode(self.file)
            options = {'quoting': '"', 'separator': ',', 'headers': True}
            record_lst = self.do_import(model_name, decoded_file, options)

            # go through our record lst and unlink any duplicated ones
            # according to our duplicate domain
            corrected_record_lst = []
            to_unlink = self.env[model_name]
            for i in range(len(record_lst)):
                record = record_lst[i]
                record_id = self.env[model_name].browse(record)
                existing_record_id = self.env[model_name].with_context(active_test=False).search(self._get_existing_record_searching_domain(record_id), limit=1)
                if existing_record_id:
                    # print(existing_record_id, record_id)
                    record = existing_record_id.id
                    to_unlink |= record_id
                    if self.name == 'purchase.charge.code':
                        existing_record_id.write({'project_opt': record_id.project_opt})
                    if self.name == 'purchase.level':
                        existing_record_id.write({'approval_min': record_id.approval_min})
                    record_id = existing_record_id
                if self.name == 'purchase.charge.code':
                    record_id.write({
                        'active': True,
                    })
                corrected_record_lst.append(record)
            to_unlink.unlink()

            if self.name == 'purchase.charge.code':
                self.env[model_name].search([('id', 'not in', corrected_record_lst)]).write({'active': False})
                # print(corrected_record_lst)
            
        return {'type': 'ir.actions.act_window_close'}
