from odoo import _, api, fields, models


class TapisAutomationJobLog(models.Model):
    _name = 'tapis.automation.job.log'
    _description = 'Automation Job Log'
    _order = 'id desc'

    job_id = fields.Many2one(
        'tapis.automation.job', string='Job', required=True, ondelete='cascade'
    )
    start_datetime = fields.Datetime(string='Start Time')
    end_datetime = fields.Datetime(string='End Time')
    duration_seconds = fields.Float(string='Duration (s)')
    status = fields.Selection([
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ], string='Status', default='running', required=True)
    records_processed = fields.Integer(string='Records', default=0)
    message = fields.Text(string='Message')
    traceback = fields.Text(string='Traceback')
    triggered_by = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('manual', 'Manual'),
    ], string='Triggered By', default='scheduled')
    user_id = fields.Many2one('res.users', string='User')
