from odoo import _, models, fields, api


class TapisCommunicationLog(models.Model):
    _name = 'tapis.communication.log'
    _description = 'Communication Log'
    _order = 'id desc'

    name = fields.Char(string='Description', readonly=True)
    template_id = fields.Many2one('tapis.communication.template', string='Template', readonly=True)
    model_name = fields.Char(string='Model', readonly=True)
    record_id = fields.Integer(string='Record ID', readonly=True)
    recipient_emails = fields.Text(string='Recipient Emails', readonly=True)
    subject = fields.Char(string='Subject', readonly=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending', required=True)
    sent_date = fields.Datetime(string='Sent Date', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    mail_message_id = fields.Many2one('mail.message', string='Mail Message', readonly=True)
    user_id = fields.Many2one('res.users', string='Triggered By', readonly=True)

    def action_resend(self):
        self.ensure_one()
        raise UserError(_('Resend via the source record.'))
