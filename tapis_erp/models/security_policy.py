from odoo import models, fields, api


class SecurityPolicy(models.Model):
    _name = 'tapis.security.policy'
    _description = 'Security Policy'
    _order = 'name'
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Policy code must be unique.'),
    ]

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)

    model_name = fields.Char(required=True, string='Target Model')
    field_names = fields.Text(string='Sensitive Fields')

    allowed_group_ids = fields.Many2many('res.groups', string='Allowed Groups')
    allowed_department_ids = fields.Many2many(
        'tapis.security.department', string='Allowed Departments'
    )
    minimum_employee_level = fields.Selection([
        ('staff', 'Staff'),
        ('supervisor', 'Supervisor'),
        ('manager', 'Manager'),
        ('director', 'Director'),
        ('executive', 'Executive'),
    ], string='Minimum Employee Level')

    hide_fields = fields.Boolean(default=False)
    readonly_fields = fields.Boolean(default=False)
    block_export = fields.Boolean(default=False)
