# -*- coding: utf-8 -*-
###############################################################################
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

{
    'name' : 'Portal Facturas',
    'version' : '1.0',
    'author' : 'Jonathan Finlay <jfinlay@riseup.net>',
    'category' : 'Accounting & Finance',
    'description' : """
Portal para facturas electronicas.
====================================

    * Portal para publicación de facturas-e

    """,
    'website': '',
    'depends' : ['website'],
    'data': [
        'data/ir_cron.xml',
        'data/auth_signup_data.xml',
        'views/auth_signup_login.xml',
        'views/ftp_view.xml',
        'views/mail_message_view.xml'
    ],
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: