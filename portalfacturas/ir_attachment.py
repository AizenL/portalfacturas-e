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

from openerp.osv import osv

class mail_message(osv.osv):

    _inherit = 'ir.attachment'

    def check(self, cr, uid, ids, mode, context=None, values=None):
        """Restricts the access to an ir.attachment, according to referred model
        In the 'document' module, it is overriden to relax this hard rule, since
        more complex ones apply there.
        """
        res_ids = {}
        require_employee = False
        if ids:
            if isinstance(ids, (int, long)):
                ids = [ids]
            cr.execute('SELECT DISTINCT res_model, res_id FROM ir_attachment WHERE id = ANY (%s)', (ids,))
            for rmod, rid in cr.fetchall():
                if not (rmod and rid):
                    require_employee = True
                    continue
                res_ids.setdefault(rmod,set()).add(rid)
        if values:
            if values.get('res_model') and values.get('res_id'):
                res_ids.setdefault(values['res_model'],set()).add(values['res_id'])

        ima = self.pool.get('ir.model.access')
        for model, mids in res_ids.items():
            # ignore attachments that are not attached to a resource anymore when checking access rights
            # (resource was deleted but attachment was not)
            if not self.pool.get(model):
                require_employee = True
                continue
            existing_ids = self.pool[model].exists(cr, uid, mids)
            if len(existing_ids) != len(mids):
                require_employee = True
            ima.check(cr, uid, model, mode)
            self.pool[model].check_access_rule(cr, uid, existing_ids, mode, context=context)
        #if require_employee:
        #    if not uid == SUPERUSER_ID and not self.pool['res.users'].has_group(cr, uid, 'base.group_user'):
        #        raise except_orm(_('Access Denied'), _("Sorry, you are not allowed to access this document."))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: