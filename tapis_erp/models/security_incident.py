from odoo import models, fields


class SecurityIncident(models.Model):
    _name = 'tapis.security.incident'
    _description = 'Security Incident'
    _order = 'incident_date desc, id desc'

    name = fields.Char(string='Description', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    model_name = fields.Char(string='Model')
    operation = fields.Char(string='Operation')
    description = fields.Text()
    incident_date = fields.Datetime(default=fields.Datetime.now)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], default='medium', required=True)
