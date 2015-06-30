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
import openerp.tools as tools

from ftplib import FTP

class FtpServer(osv.Model):
    """
    FTP Server class
    """
    _name = 'ftp.server'
    _description = 'File Transfer Protocol class'

    _columns = {
        'name': fields.char('Nombre', size=128, required=True),
        'host': fields.char('Host', size=128, required=True),
        'port': fields.integer('Puerto', required=True),
        'user': fields.char('Usuario', size=128, required=True),
        'pwd': fields.char('Contraseña', size=128),
        'active': fields.boolean('Activo'),
    }

    def test(self, cr, uid, ids, context=None):
        for ftp_server in self.browse(cr, uid, ids, context=context):
            ftp = False
            if not ftp_server.active:
                pass
            try:
                ftp = self.connect(ftp_server.host, ftp_server.port,
                                   ftp_server.user, ftp_server.pwd)
            except Exception, e:
                raise osv.except_osv("Connection Test Failed!", "Here is what we got instead:\n %s" % tools.ustr(e))
            finally:
                try:
                    if ftp: ftp.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        raise osv.except_osv("Connection Test Succeeded!", "Everything seems properly set up!")

    def connect(self, host, port, user, pwd):
        ftp = FTP()
        ftp.connect(host, port)
        ftp.login(user, pwd)
        return ftp

    def getfile(self, ftp, filename='log.txt'):
        file = open(localfile, 'w')
        ftp.retrbinary('RETR ' + filename, file.write)
        file.close()

    def putfile(self, ftp, localfile='log.txt', remotefile='log-processed.txt'):
        storecmd = 'STOR %s' % localfile
        ftp.storbinary(storecmd, open(remotefile, 'rb'))

    def quit(self, ftp):
        if ftp:
            ftp.quit()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: