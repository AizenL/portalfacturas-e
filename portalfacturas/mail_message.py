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
        'doc_extension': fields.char(u'Extensión', size=4),
        'sustento': fields.char('Sustento', size=32),
        'state': fields.selection([('to_read', 'Por leer'),
                                   ('archive', 'Archivado')], 'Estado'),
    }

    _defaults = {'state': 'to_read'}

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        """ Access rules of mail.message:
            - read: if
                - author_id == pid, uid is the author, OR
                - mail_notification (id, pid) exists, uid has been notified, OR
                - uid have read access to the related document if model, res_id
                - otherwise: raise
            - create: if
                - no model, no res_id, I create a private message OR
                - pid in message_follower_ids if model, res_id OR
                - mail_notification (parent_id.id, pid) exists, uid has been notified of the parent, OR
                - uid have write or create access on the related document if model, res_id, OR
                - otherwise: raise
            - write: if
                - author_id == pid, uid is the author, OR
                - uid has write or create access on the related document if model, res_id
                - otherwise: raise
            - unlink: if
                - uid has write or create access on the related document if model, res_id
                - otherwise: raise
        """
        def _generate_model_record_ids(msg_val, msg_ids):
            """ :param model_record_ids: {'model': {'res_id': (msg_id, msg_id)}, ... }
                :param message_values: {'msg_id': {'model': .., 'res_id': .., 'author_id': ..}}
            """
            model_record_ids = {}
            for id in msg_ids:
                vals = msg_val.get(id, {})
                if vals.get('model') and vals.get('res_id'):
                    model_record_ids.setdefault(vals['model'], set()).add(vals['res_id'])
            return model_record_ids

        if uid == SUPERUSER_ID:
            return
        if isinstance(ids, (int, long)):
            ids = [ids]
        not_obj = self.pool.get('mail.notification')
        fol_obj = self.pool.get('mail.followers')
        partner_id = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=None).partner_id.id

        # Read mail_message.ids to have their values
        message_values = dict((res_id, {}) for res_id in ids)
        cr.execute('SELECT DISTINCT id, model, res_id, author_id, parent_id FROM "%s" WHERE id = ANY (%%s)' % self._table, (ids,))
        for id, rmod, rid, author_id, parent_id in cr.fetchall():
            message_values[id] = {'model': rmod, 'res_id': rid, 'author_id': author_id, 'parent_id': parent_id}

        # Author condition (READ, WRITE, CREATE (private)) -> could become an ir.rule ?
        author_ids = []
        if operation == 'read' or operation == 'write':
            author_ids = [mid for mid, message in message_values.iteritems()
                          if message.get('author_id') and message.get('author_id') == partner_id]
        elif operation == 'create':
            author_ids = [mid for mid, message in message_values.iteritems()
                          if not message.get('model') and not message.get('res_id')]

        # Parent condition, for create (check for received notifications for the created message parent)
        notified_ids = []
        if operation == 'create':
            parent_ids = [message.get('parent_id') for mid, message in message_values.iteritems()
                          if message.get('parent_id')]
            not_ids = not_obj.search(cr, SUPERUSER_ID, [('message_id.id', 'in', parent_ids), ('partner_id', '=', partner_id)], context=context)
            not_parent_ids = [notif.message_id.id for notif in not_obj.browse(cr, SUPERUSER_ID, not_ids, context=context)]
            notified_ids += [mid for mid, message in message_values.iteritems()
                             if message.get('parent_id') in not_parent_ids]

        # Notification condition, for read (check for received notifications and create (in message_follower_ids)) -> could become an ir.rule, but not till we do not have a many2one variable field
        other_ids = set(ids).difference(set(author_ids), set(notified_ids))
        model_record_ids = _generate_model_record_ids(message_values, other_ids)
        if operation == 'read':
            not_ids = not_obj.search(cr, SUPERUSER_ID, [
                ('partner_id', '=', partner_id),
                ('message_id', 'in', ids),
            ], context=context)
            notified_ids = [notification.message_id.id for notification in not_obj.browse(cr, SUPERUSER_ID, not_ids, context=context)]
        elif operation == 'create':
            for doc_model, doc_ids in model_record_ids.items():
                fol_ids = fol_obj.search(cr, SUPERUSER_ID, [
                    ('res_model', '=', doc_model),
                    ('res_id', 'in', list(doc_ids)),
                    ('partner_id', '=', partner_id),
                ], context=context)
                fol_mids = [follower.res_id for follower in fol_obj.browse(cr, SUPERUSER_ID, fol_ids, context=context)]
                notified_ids += [mid for mid, message in message_values.iteritems()
                                 if message.get('model') == doc_model and message.get('res_id') in fol_mids]

        # CRUD: Access rights related to the document
        other_ids = other_ids.difference(set(notified_ids))
        model_record_ids = _generate_model_record_ids(message_values, other_ids)
        document_related_ids = []
        for model, doc_ids in model_record_ids.items():
            model_obj = self.pool[model]
            mids = model_obj.exists(cr, uid, list(doc_ids))
            if hasattr(model_obj, 'check_mail_message_access'):
                model_obj.check_mail_message_access(cr, uid, mids, operation, context=context)
            else:
                self.pool['mail.thread'].check_mail_message_access(cr, uid, mids, operation, model_obj=model_obj, context=context)
            document_related_ids += [mid for mid, message in message_values.iteritems()
                                     if message.get('model') == model and message.get('res_id') in mids]

        # Calculate remaining ids: if not void, raise an error
        other_ids = other_ids.difference(set(document_related_ids))
        if not other_ids:
            return
        #raise orm.except_orm(_('Access Denied'),
        #                     _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') %
        #                     (self._description, operation))

    def do_archive(self, cr, uid, ids, context=None):
        for record in self.read(cr, uid, ids, ['state']):
            if record['state'] == 'to_read':
                self.write(cr, uid, record['id'], {'state': 'archive'})
            elif record['state'] == 'archive':
                self.write(cr, uid, record['id'], {'state': 'to_read'})
        return True

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

        def get_price(file, fname):
            price = 0.0
            sustento = "No Aplica"
            if doc_extension(fname) == "xml":
                file = StringIO(file)
                file = StringIO(unescape(file.getvalue()))
                parser = etree.XMLParser(recover=True)
                tree = etree.parse(file, parser)
                if doc_type(fname) in ('fac', 'nc'):
                    file = tree.find('//comprobante').text
                    tree = etree.parse(StringIO(file))
                    price = float(tree.find('//totalSinImpuestos').text) or 0.0
                if doc_type(fname) == 'ret':
                    file = tree.find('//comprobante').text
                    tree = etree.parse(StringIO(file))
                    sustento = tree.find('//numDocSustento').text or "No Aplica"
                    if sustento != "No Aplica":
                        sustento = sustento[0:3] + "-" + sustento[3:6] + "-" + sustento[6:]
                    for value in tree.xpath('//valorRetenido'):
                        price += float(value.text)
            return price, sustento

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
            f.close()
            price, sustento = get_price(file, filename[0])
            file = base64.b64encode(file)
            document_vals = {'name': filename[0],
                             'datas': file,
                             'datas_fname': filename[0],
                             'type': 'binary',
                             'res_model': 'mail.message'
                             }
            attach_id = ir_attachment_obj.create(cr, SUPERUSER_ID, document_vals, context)
            return attach_id, price, sustento

        def create_notification(row, price=0.0, sustento="No Aplica"):
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
                         'sustento': sustento,
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
                sustento = "No Aplica"
                for file in files:
                    path = file[1].split('\\')[4]
                    attach_id = None
                    try:
                        attach_id, ret_price, ret_sustento = get_file(path, file)
                        if ret_price:
                            price = ret_price
                        if ret_sustento:
                            sustento = ret_sustento
                    except:
                        continue
                    if attach_id:
                        attach_ids.append(attach_id)
                        history_log_ids.append(file[2])
                if attach_ids:
                    mail_id = create_notification(row, price=price, sustento=sustento)
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