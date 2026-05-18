from odoo import models, fields, api


class TapisEmployee(models.Model):
    _name = 'tapis.employee'
    _description = 'Tapis Employee'

    name = fields.Char(string="Employee Name", required=True)

    role = fields.Selection([
        ('designer', 'Designer'),
        ('commercial', 'Commercial'),
        ('production', 'Production'),
        ('developer', 'Developer'),
        ('manager', 'Manager')
    ], string="Role", required=True)

    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")

    salary = fields.Float(string="Salary")
    hourly_rate = fields.Float(string="Hourly Rate", default=0.0)

    active = fields.Boolean(default=True)
    image = fields.Binary(string="Employee Image")
    production_count = fields.Integer(compute='_compute_production_count')
    document_count = fields.Integer(compute='_compute_document_count')

    @api.depends()
    def _compute_production_count(self):
        for rec in self:
            rec.production_count = self.env['tapis.production'].search_count([('employee_ids', '=', rec.id)])

    def action_view_productions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Productions',
            'res_model': 'tapis.production',
            'view_mode': 'tree,form',
            'domain': [('employee_ids', '=', self.id)],
            'target': 'current',
        }

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('employee_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
            'target': 'current',
        }
