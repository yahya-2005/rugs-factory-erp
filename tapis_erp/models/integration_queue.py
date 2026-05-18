import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TapisIntegrationQueue(models.Model):
    _name = 'tapis.integration.queue'
    _description = 'Integration Queue'
    _order = 'create_date desc'

    name = fields.Char(string='Description')
    model_name = fields.Char(required=True)
    record_id = fields.Integer(required=True)
    operation_type = fields.Selection([
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('sync', 'Sync'),
        ('export', 'Export'),
        ('import', 'Import'),
    ], required=True, default='sync')
    payload = fields.Text(string='Payload (JSON)')

    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='pending', required=True)
    retry_count = fields.Integer(default=0)
    next_retry_datetime = fields.Datetime()
    last_error = fields.Text()

    connection_id = fields.Many2one('tapis.api.connection', string='Connection')
    endpoint_id = fields.Many2one('tapis.api.endpoint', string='Endpoint')

    @api.model
    def enqueue(self, model_name, record_id, operation_type='sync', payload=None, connection_id=None, endpoint_id=None):
        vals = {
            'model_name': model_name,
            'record_id': record_id,
            'operation_type': operation_type,
            'payload': json.dumps(payload) if payload else '{}',
            'state': 'pending',
            'connection_id': connection_id,
            'endpoint_id': endpoint_id,
        }
        return self.create(vals)

    def action_process(self):
        for item in self:
            if item.state != 'pending':
                continue
            item.state = 'processing'
            try:
                conn = item.connection_id
                endpoint = item.endpoint_id
                if conn and endpoint:
                    payload = json.loads(item.payload) if item.payload else {}
                    result = endpoint.call_endpoint(request_data=payload)
                    item.write({'state': 'done', 'last_error': False})
                else:
                    item.write({'state': 'done'})
            except Exception as e:
                import traceback
                item.write({
                    'state': 'failed',
                    'last_error': str(e),
                    'retry_count': item.retry_count + 1,
                })
                _logger.error('Queue item %d failed: %s\n%s', item.id, e, traceback.format_exc())

    @api.model
    def process_queue(self):
        items = self.search([('state', '=', 'pending')], limit=50)
        items.action_process()
        return len(items)

    @api.model
    def retry_failed(self):
        items = self.search([('state', '=', 'failed')])
        for item in items:
            item.state = 'pending'
        items.action_process()
        return len(items)
