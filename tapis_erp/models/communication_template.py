from odoo import _, models, fields, api
from odoo.exceptions import UserError
import json


class TapisCommunicationTemplate(models.Model):
    _name = 'tapis.communication.template'
    _description = 'Communication Template'
    _order = 'code'

    name = fields.Char(string='Template Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(string='Active', default=True)
    model_name = fields.Char(string='Target Model', required=True, help="e.g. tapis.crm.lead")
    trigger_event = fields.Selection([
        ('create', 'On Create'),
        ('write', 'On Write'),
        ('state_change', 'On State Change'),
        ('scheduled', 'Scheduled (Cron)'),
        ('manual', 'Manual'),
    ], string='Trigger Event', required=True, default='manual')
    email_subject = fields.Char(string='Email Subject', required=True)
    email_body = fields.Html(string='Email Body', required=True)
    recipient_type = fields.Selection([
        ('specific_users', 'Specific Users'),
        ('record_owner', 'Record Owner'),
        ('manager', 'Manager'),
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
    ], string='Recipient Type', required=True, default='record_owner')
    user_ids = fields.Many2many('res.users', string='Recipient Users')
    send_email = fields.Boolean(string='Send Email', default=True)
    create_activity = fields.Boolean(string='Create Activity', default=False)
    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type')
    condition_domain = fields.Text(string='Condition Domain', help="JSON-encoded domain for matching records")
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Template code must be unique.'),
    ]

    @api.constrains('recipient_type', 'user_ids')
    def _check_recipients(self):
        for rec in self:
            if rec.recipient_type == 'specific_users' and not rec.user_ids:
                raise UserError(_('Please specify at least one recipient user.'))
