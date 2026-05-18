from odoo import models, fields


class TapisAuditLog(models.Model):
    _name = 'tapis.audit.log'
    _description = 'Audit Log'
    _order = 'id desc'

    name = fields.Char(string='Description', readonly=True)
    model_name = fields.Char(string='Model', required=True, readonly=True)
    record_id = fields.Integer(string='Record ID', required=True, readonly=True)
    record_name = fields.Char(string='Record Name', readonly=True)

    user_id = fields.Many2one('res.users', string='User', required=True, readonly=True)
    employee_id = fields.Many2one('tapis.employee', string='Employee', readonly=True)

    action_type = fields.Selection([
        ('create', 'Created'),
        ('write', 'Updated'),
        ('unlink', 'Deleted'),
    ], string='Action', required=True, readonly=True)
    action_date = fields.Datetime(string='Date', default=fields.Datetime.now, readonly=True)

    field_name = fields.Char(string='Field', readonly=True)
    field_label = fields.Char(string='Field Label', readonly=True)
    old_value = fields.Text(string='Old Value', readonly=True)
    new_value = fields.Text(string='New Value', readonly=True)

    ip_address = fields.Char(string='IP Address', readonly=True)
    user_agent = fields.Text(string='User Agent', readonly=True)

    module_name = fields.Char(string='Module', readonly=True)
    description = fields.Text(string='Description', readonly=True)
