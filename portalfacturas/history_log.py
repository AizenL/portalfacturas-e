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

class history_log(osv.Model):
    _name = 'history.log'
    _description = 'History log table'

    _columns = {
        'name': fields.char('Archivo', size=256, required=True),
        'path': fields.char('Ruta', size=512, required=True),
        'date': fields.datetime('Fecha', required=True),
        'value': fields.float('Valor'),
        'state': fields.selection([
            ('processed', 'Procesada'),
            ('no_processed', 'No procesada'),
            ('exception', 'En excepción')
        ], 'Estado', required=True),
    }

    _defaults = {
        'state': 'no_processed',
    }

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'El nombre del documento debe ser unico')
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: