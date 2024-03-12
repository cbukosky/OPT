# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.


from odoo import models, fields
import xlwt
from io import BytesIO
import base64
import json


class Excel(models.Model):
    _name = "sh.bom.structure.xls"
    _description = "BOM Structure Report in XLS"

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def bom_structure_report(self):

        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.bom.structure.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class BOMStructureExcel(models.Model):
    _inherit = 'mrp.bom'

    def _bom_structure_excel(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;align: horiz left')
        bold = xlwt.easyxf(
            'font:bold True;align: horiz left')
        price_style = xlwt.easyxf(
            'align: horiz right')
        final_price = xlwt.easyxf(
            'font:bold True;align: horiz right')
        header = xlwt.easyxf(
            'font:bold True;align: horiz center')
        worksheet = workbook.add_sheet("Excel Report")
        row = 0
        column = 0
        worksheet.col(column).width = int(25*260)
        worksheet.write_merge(
            row, row+1, column, column+5, 'BoM Structure & Cost', heading_format)
        if self.product_tmpl_id.display_name:
            worksheet.write_merge(
                row+2, row+3, column, column+5, self.product_tmpl_id.display_name, bold)
        row = row+5
        bom_line_list = ['Product', 'BoM',
                         'Quantity', 'Unit of Measure', 'Product Cost', 'BoM Cost']
        report_obj = self.env['report.mrp.report_bom_structure']
        docs = []
        data = {}
        for bom_id in [self.id]:
            bom = report_obj.env['mrp.bom'].browse(bom_id)
            variant = data.get('variant')
            candidates = variant and report_obj.env['product.product'].browse(
                variant) or bom.product_id or bom.product_tmpl_id.product_variant_ids
            quantity = float(data.get('quantity', bom.product_qty))
            for product_variant_id in candidates.ids:
                if data and data.get('childs'):
                    doc = report_obj._get_pdf_line(bom_id, product_id=product_variant_id, qty=quantity, child_bom_ids=set(
                        json.loads(data.get('childs'))))
                else:
                    doc = report_obj._get_pdf_line(
                        bom_id, product_id=product_variant_id, qty=quantity, unfolded=True)
                docs.append(doc)
            if not candidates:
                if data and data.get('childs'):
                    doc = report_obj._get_pdf_line(bom_id, qty=quantity, child_bom_ids=set(
                        json.loads(data.get('childs'))))
                else:
                    doc = report_obj._get_pdf_line(
                        bom_id, qty=quantity, unfolded=True)
                docs.append(doc)
        if self.code:
            worksheet.write(row, 0, "Reference : "+str(self.code), bold)
            row += 2

        for line in bom_line_list:
            if (column == 0) and (column == 1):
                worksheet.col(column).width = int(25*520)
            else:
                worksheet.col(column).width = int(25*150)
            worksheet.write(row, column, line, header)
            column += 1
        row += 1

        if docs[0]['bom_prod_name']:
            worksheet.write(row, 0, docs[0]['bom_prod_name'])
        if docs[0]['code']:
            worksheet.write(row, 1, docs[0]['code'])
        if docs[0]['bom_qty']:
            worksheet.write(row, 2, str(
                "{:.2f}".format(docs[0]['bom_qty'])), price_style)
        if docs[0]['price']:
            worksheet.write(row, 4, str(
                docs[0]['currency'].symbol)+' '+str(
                "{:.2f}".format(docs[0]['price'])), price_style)
        if docs[0]['total']:
            worksheet.write(row, 5, str(
                docs[0]['currency'].symbol)+' '+str(
                "{:.2f}".format(docs[0]['total'])), price_style)
        row += 1
        for line in docs[0]['lines']:
            worksheet.col(0).width = int(25*520)
            worksheet.col(1).width = int(25*520)
            space = '       '
            if 'level' in line:
                if line['level'] != 0:
                    worksheet.write(
                        row, 0,  line['level']*(space)+str(line['name']))
                else:
                    worksheet.write(row, 0, line['name'])
            if 'code' in line:
                worksheet.write(row, 1, line['code'])
            if 'quantity' in line:
                worksheet.write(row, 2, str(
                    "{:.2f}".format(line['quantity'])), price_style)
            if 'uom' in line:
                worksheet.write(row, 3, line['uom'], price_style)
            if 'prod_cost' in line:
                worksheet.write(row, 4, str(
                    docs[0]['currency'].symbol)+' '+str("{:.2f}".format(line['prod_cost'])), price_style)
            if 'bom_cost' in line:
                worksheet.write(row, 5, str(
                    docs[0]['currency'].symbol)+' '+str("{:.2f}".format(line['bom_cost'])), price_style)
            row += 1
        worksheet.write(row, 3, 'Unit Cost', final_price)
        worksheet.write(row, 4, str(
            docs[0]['currency'].symbol)+' '+str("{:.2f}".format(docs[0]['price'])), final_price)
        worksheet.write(row, 5, str(
            docs[0]['currency'].symbol)+' '+str("{:.2f}".format(docs[0]['total'])), final_price)
        filename = ('BoM Structure  Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['sh.bom.structure.xls'].sudo().create({
            'excel_file': base64.encodebytes(fp.getvalue()),
            'file_name': filename,
        })
        return{
            'type': 'ir.actions.act_window',
            'res_id': export_id.id,
            'res_model': 'sh.bom.structure.xls',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }
