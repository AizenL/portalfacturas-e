# -*- coding: utf-8 -*-
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
from openerp.osv import osv, fields

class FtpServer(osv.Model):
    """
    FTP Server class
    """
    _name = 'ftp.server'
    _description = 'File Transfer Protocol class'

    _columns = {
        'name': fields.char('Nombre', size=128),
        'host': fields.char('Host', size=128),
        'port': fields.integer('Puerto'),
        'user': fields.char('Usuario', size=128),
        'pwd': fields.char('Contraseña', size=128),
    }

    def connect(self, cr, uid, context=None):
        ftp_obj = self.pool.get('ftp.server')
        ftp_obj.read(cr, uid, [], context=context)
        from ftplib import FTP
        ftp = FTP()
        try:
            ftp.connect(ftp_obj.host, ftp_obj.port)
            ftp.login(ftp_obj.user, ftp_obj.pwd)
        except '[Errno 101] Network is unreachable':
            raise osv.except_osv('Error 101', 'Network is unreachable')
        except:
            self.connect(cr, uid, context=context)
        return ftp

    def walk(self, cr, uid, ruc, context=None):
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: