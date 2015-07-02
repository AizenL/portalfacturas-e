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
    }

    def mime_type(self, file):
        ext = file.split('.')[1]
        if ext == "pdf":
            return 'application/pdf'
        elif ext == "xml":
            return 'application/xml'

    def doc_type(self, filename):
        type = filename.split('_')[0]
        return type.lower()

    def process_log(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        """
        Cron activity to get all new documents for current users
        """
        ftp_obj = self.pool.get('ftp.server')
        history_obj = self.pool.get('history.log')
        ftp = ftp_obj.createconnection(cr, uid, context=context)
        ftp_obj.getfile(ftp)
        file = open('log.txt', 'r')
        ftp.quit()
        for line in file.readlines():
            line.replace('\n', '')
            line = line.split('\t')
            if len(line) != 3:
                continue
            vals = {'name': line[0], 'path': line[1], 'date': line[2].replace('\n', '')}
            try:
                history_obj.create(cr, uid, vals, context=context)
            except Exception:
                cr.execute("ROLLBACK;")
                pass
        return {}

    def load_invoices(self, cr, uid, automatic=False, use_new_cursor=False, context=None):
        """
        Load users's invoices
        """
        user_obj = self.pool.get('res.users')
        ids = user_obj.search(cr, uid, [('vat', '!=', False)], context=context)
        mail_obj = self.pool.get('mail.message')
        ir_attachment_obj = self.pool.get('ir.attachment')
        select_query = "SELECT \"name\", \"path\", \"id\" FROM history_log " \
                       "WHERE \"path\" like '%%%s%%' and \"state\" != 'processed'"
        for user in user_obj.browse(cr, uid, ids, context=context):
            vat = user.vat
            vat = vat.replace('-', '')
            cr.execute(select_query % vat)
            for row in cr.fetchall():
                path = row[1].split('\\')[4]
                ftp_obj = self.pool.get('ftp.server')
                ftp = ftp_obj.createconnection(cr, uid, context=context)
                ftp.cwd(path)
                ftp_obj.getfile(ftp, row[0])
                ftp.quit()
                file = open(row[0], 'r')
                file = base64.b64encode(file.read())
                document_vals = {'name': row[0],
                                 'datas': file,
                                 'datas_fname': row[0],
                                 'type': 'binary',
                                 'doc_type': self.doc_type(row[0])
                                 }
                attach_id = ir_attachment_obj.create(cr, uid, document_vals, context)
                mail_vals = {'subject': 'Nuevo documento %s' % row[0].replace('_', '-'),
                             'body': 'Un nuevo documento esta disponible',
                             'author_id': 1,
                             'type': 'notification',
                             'subtype_id': 1,
                             }
                mail_id = mail_obj.create(cr, uid, mail_vals, context=context)
                cr.execute("INSERT INTO mail_message_res_partner_rel(\"mail_message_id\", \"res_partner_id\") "
                           "VALUES ('%s', '%s')" % (mail_id, user.partner_id.id))
                cr.execute("INSERT INTO message_attachment_rel(\"message_id\", \"attachment_id\") "
                           "VALUES ('%s', '%s')" % (mail_id, attach_id))
                cr.execute("INSERT INTO mail_notification(\"is_read\", \"starred\", \"partner_id\", \"message_id\") "
                           "VALUES ('%s', '%s', '%s', '%s')" % ('FALSE', 'FALSE', user.partner_id.id, mail_id))
                cr.execute("UPDATE history_log SET state = 'processed' WHERE id = '%s'" % row[2])

                # TODO: Proceso que vacie el archivo de log
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: