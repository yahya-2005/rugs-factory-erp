from odoo import models, fields


class Users(models.Model):
    _inherit = 'res.users'

    security_department_id = fields.Many2one('tapis.security.department', string='Security Department')
    employee_level = fields.Selection([
        ('staff', 'Staff'),
        ('supervisor', 'Supervisor'),
        ('manager', 'Manager'),
        ('director', 'Director'),
        ('executive', 'Executive'),
    ], string='Employee Level', default='staff')
    can_view_financial_data = fields.Boolean(string='Can View Financial Data', default=False)
    can_export_sensitive_data = fields.Boolean(string='Can Export Sensitive Data', default=False)
    data_access_scope = fields.Selection([
        ('own', 'Own Records Only'),
        ('department', 'Department Records'),
        ('company', 'All Company Records'),
        ('global', 'Global Access'),
    ], string='Data Access Scope', default='own', required=True)
