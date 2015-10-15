# -*- coding: utf-8 -*-
################################################################################
#    Copyright (C) 2015  Jonathan Finlay <jfinlay@riseup.net>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################

from openerp.osv import osv, fields
import base64
import os

from openerp import SUPERUSER_ID

class mail_message(osv.Model):

    _inherit = 'mail.message'

    _columns = {
        'doc_type': fields.selection(
            [
                ('fac', 'Factura'),
                ('nc', 'Nota de crédito'),
                ('gui', 'Guia de remisión'),
                ('ret', 'Retención')
            ], 'Tipo de documento'),
        'doc_name': fields.char('Nombre', size=256),
        'doc_value': fields.float('Valor'),
        'doc_extension': fields.char(u'Extensión', size=4)
    }

    def mime_type(self, file):
        ext = file.split('.')[1]
        if ext == "pdf":
            return 'application/pdf'
        elif ext == "xml":
            return 'application/xml'

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        self.load_invoices(cr, uid, context=context)
        return super(mail_message, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)

    def process_log(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        """
        Cron activity to get all new documents for current users
        """
        if os.path.isfile("log.txt"):
            os.remove("log.txt")
        ftp_obj = self.pool.get('ftp.server')
        history_obj = self.pool.get('history.log')
        ftp = ftp_obj.createconnection(cr, uid, context=context)
        ftp_obj.getfile(ftp)
        file = open('log.txt', 'r')
        ftp.quit()
        for line in file.readlines():
            line.replace('\n', '')
            line = line.split('\t')
            if len(line) != 4:
                continue
            vals = {'name': line[0], 'path': line[1], 'date': line[2].replace('\n', ''), 'value': line[3]}
            confirm_query = "select name from history_log WHERE name = '%s'"
            cr.execute(confirm_query % (vals['name']))
            if cr.fetchone():
                continue
            try:
                history_obj.create(cr, uid, vals, context=context)
            except Exception:
                cr.execute("ROLLBACK;")
                pass
        return {}

    def load_invoices(self, cr, uid, context=None):
        """
        Load users's invoices
        """
        def correct_name(filename):
            """
            Check if file name is correct
            """
            return filename.find('\\') > 0

        def doc_type(filename, index=0):
            """
            Return type of file RET, FAC, GUI, NC
            """
            type = filename.split('_')[index]
            return type.lower()

        user_obj = self.pool.get('res.users')
        ids = user_obj.search(cr, uid, [('vat', '!=', False), ('id', '=', uid)], context=context)
        mail_obj = self.pool.get('mail.message')
        ir_attachment_obj = self.pool.get('ir.attachment')

        os.chdir("/tmp")

        select_query = "SELECT \"name\", \"path\", \"id\", \"date\", \"value\" FROM history_log " \
                       "WHERE \"path\" like '%%%s%%' and \"state\" != 'processed'"
        for user in user_obj.browse(cr, uid, ids, context=context):
            vat = user.vat
            vat = vat.replace('-', '')
            cr.execute(select_query % vat)
            datas = cr.fetchall()
            for row in datas:
                if correct_name(row[0]):
                    continue
                path = row[1].split('\\')[4]
                ftp_obj = self.pool.get('ftp.server')
                ftp = ftp_obj.createconnection(cr, SUPERUSER_ID, context=context)
                try:
                    ftp.cwd(path)
                    ftp_obj.getfile(ftp, row[0])
                except:
                    continue
                ftp.quit()
                file = open(row[0], 'r')
                file = base64.b64encode(file.read())
                document_vals = {'name': row[0],
                                 'datas': file,
                                 'datas_fname': row[0],
                                 'type': 'binary'
                                 }
                attach_id = ir_attachment_obj.create(cr, SUPERUSER_ID, document_vals, context)
                doc_name = row[0].replace('_', '-')
                mail_vals = {'subject': 'Nuevo documento %s' % doc_name,
                             'body': 'Un nuevo documento esta disponible',
                             'author_id': 1,
                             'type': 'notification',
                             'subtype_id': 1,
                             'doc_type': doc_type(row[0]),
                             'doc_name': row[0],
                             'doc_value': row[3],
                             'doc_extension': row[0].split('.')[1],
                             'date': row[3]
                             }

                mail_id = mail_obj.create(cr, SUPERUSER_ID, mail_vals, context=context)
                cr.execute("INSERT INTO mail_message_res_partner_rel(\"mail_message_id\", \"res_partner_id\") "
                           "VALUES ('%s', '%s')" % (mail_id, user.partner_id.id))
                cr.execute("INSERT INTO message_attachment_rel(\"message_id\", \"attachment_id\") "
                           "VALUES ('%s', '%s')" % (mail_id, attach_id))
                cr.execute("INSERT INTO mail_notification(\"is_read\", \"starred\", \"partner_id\", \"message_id\") "
                           "VALUES ('%s', '%s', '%s', '%s')" % ('FALSE', 'FALSE', user.partner_id.id, mail_id))
                cr.execute("UPDATE history_log SET state = 'processed' WHERE id = '%s'" % row[2])

        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: