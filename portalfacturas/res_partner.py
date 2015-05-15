#
# Copyright (C) 2015  Jonathan Finlay <jfinlay@riseup.net>
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

from openerp.osv import fields, osv
from stdnum import ec

class res_partner(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'vat': fields.char('C.I. / R.U.C.',
                           help="Identificacion del cliente, se excluyen '-' u otros caracteres")
    }

    def vat_check(self, cr, uid, vat, context=None):
        res = True
        if ec.ci.is_valid(vat) or ec.ruc.is_valid(vat):
            pass
        else:
            return False
        return True

    _sql_constraints = [('unique_vat', 'unique(vat)', 'Ya existe un usuario con esta C.I./R.U.C.')]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: