import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class TapisApiLog(models.Model):
    _name = 'tapis.api.log'
    _description = 'API Log'
    _order = 'request_datetime desc'

    connection_id = fields.Many2one('tapis.api.connection', string='Connection', ondelete='cascade')
    endpoint_id = fields.Many2one('tapis.api.endpoint', string='Endpoint', ondelete='set null')

    request_datetime = fields.Datetime(string='Request Time', default=fields.Datetime.now, required=True)
    response_datetime = fields.Datetime(string='Response Time')
    duration_seconds = fields.Float(string='Duration (s)')

    request_url = fields.Char(string='URL')
    request_method = fields.Char(string='Method')
    request_headers = fields.Text(string='Request Headers')
    request_body = fields.Text(string='Request Body')

    response_status_code = fields.Integer(string='Status Code')
    response_headers = fields.Text(string='Response Headers')
    response_body = fields.Text(string='Response Body')

    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retried', 'Retried'),
    ], default='success', required=True)
    attempt_number = fields.Integer(default=1)
    error_message = fields.Text(string='Error Message')

    def action_view_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tapis.api.log',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
