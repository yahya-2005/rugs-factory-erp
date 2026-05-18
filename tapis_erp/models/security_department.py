from odoo import models, fields, api


class SecurityDepartment(models.Model):
    _name = 'tapis.security.department'
    _description = 'Security Department'
    _order = 'name'
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Department code must be unique.'),
    ]

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    manager_user_id = fields.Many2one('res.users', string='Department Manager')
    user_ids = fields.Many2many('res.users', string='Members')
    active = fields.Boolean(default=True)
    description = fields.Text()
