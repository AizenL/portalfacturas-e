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

from lxml import etree
from xml.sax.saxutils import unescape
from StringIO import StringIO

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
            Return type of file: ret, fac, gui, nc
            """
            type = filename.split('_')[index]
            return type.lower()

        def doc_name(filename):
            """
            Get filename
            :param filename:
            :return: name_of_file_without_extension
            """
            return filename.split('.')[0]

        def doc_extension(filename):
            """
            Get filename
            :param filename:
            :return: name_of_file_without_extension
            """
            return filename.split('.')[1]

        def get_file(path, filename):
            """
            Get file from ftp server
            :param path: path of file in server
            :param filename: name of file in ftp server
            :return: attach_id & price
            """
            ftp_obj = self.pool.get('ftp.server')
            ftp = ftp_obj.createconnection(cr, SUPERUSER_ID, context=context)
            try:
                ftp.cwd(path)
                ftp_obj.getfile(ftp, filename[0])
            except:
                return 0
            ftp.quit()
            f = open(filename[0])
            file = f.read()
            file64 = file
            f.close()

            price = 0.0
            if doc_type(filename[0]) in ('fac', 'nc') and doc_extension(filename[0]) == "xml":
                xml = StringIO(file)
                xml = StringIO(unescape(xml.getvalue()))
                parser = etree.XMLParser(recover=True)
                tree = etree.parse(xml, parser)
                document = tree.find('//comprobante').text
                tree = etree.parse(StringIO(document))
                price = float(tree.find('//totalSinImpuestos').text) or 0.0

            file64 = base64.b64encode(file64)
            document_vals = {'name': filename[0],
                             'datas': file64,
                             'datas_fname': filename[0],
                             'type': 'binary',
                             'res_model': 'mail.message'
                             }
            attach_id = ir_attachment_obj.create(cr, SUPERUSER_ID, document_vals, context)
            return attach_id, price

        def create_notification(row, price=0.0):
            """
            Create notification
            :param row: history log record
            :param price: price of document
            :return: notification_id
            """
            doc_name = row[0].replace('_', '-')
            mail_vals = {'subject': 'Nuevo documento %s' % doc_name,
                         'body': 'Un nuevo documento esta disponible',
                         'author_id': 1,
                         'type': 'notification',
                         'subtype_id': 1,
                         'doc_type': doc_type(row[0]),
                         'doc_name': row[0].split(".")[0],
                         'doc_value': price,
                         'doc_extension': row[0].split('.')[1],
                         'date': row[3]
                         }

            mail_id = mail_obj.create(cr, SUPERUSER_ID, mail_vals, context=context)
            return mail_id

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
                cr.execute("SELECT \"name\", \"path\", \"id\", \"date\", \"value\" FROM history_log "
                           "WHERE \"name\" like '%%%s%%' and \"state\" != 'processed'" % doc_name(row[0]))
                files = cr.fetchall()
                attach_ids = []
                history_log_ids = []
                price = 0.0
                for file in files:
                    path = file[1].split('\\')[4]
                    attach_id = None
                    #try:
                    attach_id, ret_price = get_file(path, file)
                    if ret_price:
                        price = ret_price
                    #except:
                    #    continue
                    if attach_id:
                        attach_ids.append(attach_id)
                        history_log_ids.append(file[2])
                if attach_ids:
                    mail_id = create_notification(row, price=price)
                    cr.execute("INSERT INTO mail_message_res_partner_rel(\"mail_message_id\", \"res_partner_id\") "
                               "VALUES ('%s', '%s')" % (mail_id, user.partner_id.id))
                    for attach_id in attach_ids:
                        cr.execute("INSERT INTO message_attachment_rel(\"message_id\", \"attachment_id\") "
                                   "VALUES ('%s', '%s')" % (mail_id, attach_id))
                    cr.execute("INSERT INTO mail_notification(\"is_read\", \"starred\", \"partner_id\", \"message_id\")"
                               " VALUES ('%s', '%s', '%s', '%s')" % ('FALSE', 'FALSE', user.partner_id.id, mail_id))
                    if len(history_log_ids) == 1:
                        history_log_ids = str(tuple(history_log_ids)).replace(",", "")
                    else:
                        history_log_ids = str(tuple(history_log_ids))
                    cr.execute("UPDATE history_log SET state = 'processed' WHERE id in %s" % history_log_ids)
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: