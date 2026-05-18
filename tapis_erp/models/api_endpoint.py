import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TapisApiEndpoint(models.Model):
    _name = 'tapis.api.endpoint'
    _description = 'API Endpoint'
    _order = 'sequence'

    connection_id = fields.Many2one('tapis.api.connection', string='Connection', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    http_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ], required=True, default='GET')
    endpoint_path = fields.Char(required=True, help='e.g. /api/v1/customers')
    request_template = fields.Text(string='Request Body Template (JSON)',
                                   help='Static or dynamic JSON body template')
    header_template = fields.Text(string='Header Overrides (JSON)')

    response_mapping = fields.Text(string='Response Mapping (JSON)',
                                   help='Map response fields to Odoo fields: {\"external_id\": \"field_name\"}')
    success_codes = fields.Char(default='200,201,202', help='Comma-separated HTTP status codes considered success')

    integration_event = fields.Char(string='Integration Event',
                                    help='Event code that triggers this endpoint (e.g. sale.confirmed)')

    def call_endpoint(self, request_data=None, extra_headers=None):
        self.ensure_one()
        conn = self.connection_id
        if not conn:
            raise UserError(_('No connection configured for this endpoint.'))

        headers = {}
        if self.header_template:
            try:
                headers.update(json.loads(self.header_template))
            except (json.JSONDecodeError, TypeError):
                pass
        if extra_headers:
            headers.update(extra_headers)

        body = request_data
        if not body and self.request_template:
            try:
                body = json.loads(self.request_template)
            except (json.JSONDecodeError, TypeError):
                body = self.request_template

        return conn.call_api(self.endpoint_path, self.http_method, request_data=body, header_extra=headers)
