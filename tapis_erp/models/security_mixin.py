from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SecurityMixin(models.AbstractModel):
    _name = 'tapis.security.mixin'
    _description = 'Security Mixin'

    def _get_owner_field(self):
        return 'user_id'

    def _get_assigned_field(self):
        return False

    def _get_sensitive_fields(self):
        return []

    def _check_data_access(self, records):
        user = self.env.user
        if user.has_group('tapis_erp.group_security_manager'):
            return True
        if user.data_access_scope == 'global':
            return True
        if user.data_access_scope == 'company':
            return True
        if user.data_access_scope == 'department':
            if user.security_department_id:
                dept_user_ids = user.security_department_id.user_ids.ids
                for rec in records:
                    owner_field = self._get_owner_field()
                    owner = rec[owner_field] if owner_field and owner_field in rec else rec.create_uid
                    owner_id = owner.id if owner else False
                    if owner_id and owner_id not in dept_user_ids:
                        raise UserError(_(
                            'You can only access records from your department (%s).'
                        ) % user.security_department_id.name)
                return True
        if user.data_access_scope == 'own':
            for rec in records:
                owner_field = self._get_owner_field()
                owner = rec[owner_field] if owner_field and owner_field in rec else rec.create_uid
                owner_id = owner.id if owner else False
                if owner_id and owner_id != user.id:
                    raise UserError(_('You can only access your own records.'))
            return True
        return False

    def _check_sensitive_fields(self, fields_to_check=False):
        self.ensure_one()
        user = self.env.user
        sensitive = self._get_sensitive_fields()
        if not sensitive:
            return True
        policy = self.env['tapis.security.policy'].search([
            ('model_name', '=', self._name),
            ('active', '=', True),
        ], limit=1)
        if not policy:
            return True
        if policy.allowed_group_ids and user.groups_id & policy.allowed_group_ids:
            return True
        if policy.allowed_department_ids and user.security_department_id in policy.allowed_department_ids:
            return True
        if policy.minimum_employee_level:
            levels = ['staff', 'supervisor', 'manager', 'director', 'executive']
            user_level_idx = levels.index(user.employee_level) if user.employee_level in levels else -1
            min_idx = levels.index(policy.minimum_employee_level)
            if user_level_idx >= min_idx:
                return True
        return False

    def _check_segregation_duties(self, operation=False):
        return True

    def _log_security_incident(self, model_name, operation, description, severity='medium'):
        self.env['tapis.security.incident'].create({
            'name': _('Security: %s on %s') % (operation, model_name),
            'user_id': self.env.user.id,
            'model_name': model_name,
            'operation': operation,
            'description': description,
            'severity': severity,
        })

    @api.model
    def _check_export_permission(self):
        user = self.env.user
        if user.has_group('tapis_erp.group_security_manager'):
            return True
        if user.can_export_sensitive_data:
            return True
        policy = self.env['tapis.security.policy'].search([
            ('model_name', '=', self._name),
            ('active', '=', True),
            ('block_export', '=', True),
        ], limit=1)
        if policy:
            self._log_security_incident(
                self._name, 'export_blocked',
                _('User %s attempted to export data from %s but was blocked by policy %s.')
                % (user.name, self._name, policy.name),
                'high'
            )
            return False
        return True
