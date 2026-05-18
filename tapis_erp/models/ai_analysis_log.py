from odoo import models, fields


class AiAnalysisLog(models.Model):
    _name = 'tapis.ai.analysis.log'
    _description = 'AI Analysis Log'
    _order = 'request_datetime desc'

    design_id = fields.Many2one('tapis.design', string='Design', required=True, ondelete='cascade')
    provider_id = fields.Many2one('tapis.ai.provider', string='AI Provider', required=True)
    request_datetime = fields.Datetime(string='Request Time', default=fields.Datetime.now)
    response_datetime = fields.Datetime(string='Response Time')
    duration_seconds = fields.Float(string='Duration (s)')
    prompt_used = fields.Text(string='Prompt Used')
    raw_response = fields.Text(string='Raw Response')
    parsed_json = fields.Text(string='Parsed JSON')
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='success')
    error_message = fields.Text(string='Error Message')
