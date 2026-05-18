import logging
import json
import requests
import time
import traceback
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TapisApiConnection(models.Model):
    _name = 'tapis.api.connection'
    _description = 'API Connection'
    _inherit = ['tapis.audit.mixin']
    _order = 'name asc'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    connection_type = fields.Selection([
        ('rest', 'REST API'),
        ('graphql', 'GraphQL'),
        ('webhook', 'Webhook'),
        ('soap', 'SOAP'),
    ], required=True, default='rest')

    auth_type = fields.Selection([
        ('none', 'No Authentication'),
        ('api_key', 'API Key'),
        ('bearer_token', 'Bearer Token'),
        ('basic', 'Basic Auth'),
        ('oauth2', 'OAuth2 Client Credentials'),
    ], default='none')

    api_key = fields.Char(string='API Key')
    bearer_token = fields.Char(string='Bearer Token')
    username = fields.Char()
    password = fields.Char()
    client_id = fields.Char()
    client_secret = fields.Char()
    token_url = fields.Char(string='Token URL')
    access_token = fields.Char(readonly=True)
    token_expiry = fields.Datetime(readonly=True)

    base_url = fields.Char(required=True)
    timeout_seconds = fields.Integer(default=60)
    verify_ssl = fields.Boolean(default=True)

    default_headers = fields.Text(string='Default Headers (JSON)')

    requests_per_minute = fields.Integer(default=60)
    max_retries = fields.Integer(default=3)
    retry_interval_seconds = fields.Integer(default=30)

    endpoint_ids = fields.One2many('tapis.api.endpoint', 'connection_id', string='Endpoints')
    log_ids = fields.One2many('tapis.api.log', 'connection_id', string='Logs')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Connection code must be unique!'),
    ]

    def action_test_connection(self):
        self.ensure_one()
        test_endpoint = self.endpoint_ids[:1]
        if not test_endpoint:
            headers = self._get_auth_headers()
            try:
                resp = requests.get(self.base_url, headers=headers, timeout=self.timeout_seconds,
                                    verify=self.verify_ssl)
                if resp.ok:
                    raise UserError(_('Connection successful! Status: %d') % resp.status_code)
                raise UserError(_('Connection failed! Status: %d - %s') % (resp.status_code, resp.text[:200]))
            except requests.RequestException as e:
                raise UserError(_('Connection error: %s') % str(e))
        try:
            test_endpoint.call_endpoint()
            raise UserError(_('Connection and endpoint test successful!'))
        except UserError:
            raise
        except Exception as e:
            raise UserError(_('Connection test failed: %s') % str(e))

    def action_generate_token(self):
        self.ensure_one()
        if self.auth_type != 'oauth2':
            raise UserError(_('Token generation is only available for OAuth2 connections.'))
        if not self.token_url or not self.client_id or not self.client_secret:
            raise UserError(_('Token URL, Client ID, and Client Secret are required.'))
        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }
            resp = requests.post(self.token_url, data=data, timeout=self.timeout_seconds, verify=self.verify_ssl)
            if resp.ok:
                token_data = resp.json()
                self.access_token = token_data.get('access_token', '')
                expires_in = token_data.get('expires_in', 3600)
                self.token_expiry = fields.Datetime.now() + timedelta(seconds=int(expires_in))
                raise UserError(_('Token generated successfully!'))
            raise UserError(_('Token generation failed: %s') % resp.text[:500])
        except requests.RequestException as e:
            raise UserError(_('Token request failed: %s') % str(e))

    def _get_auth_headers(self):
        headers = {}
        if self.default_headers:
            try:
                headers.update(json.loads(self.default_headers))
            except (json.JSONDecodeError, TypeError):
                pass
        if self.auth_type == 'api_key':
            headers['X-API-Key'] = self.api_key or ''
        elif self.auth_type == 'bearer_token':
            headers['Authorization'] = 'Bearer %s' % (self.bearer_token or '')
        elif self.auth_type == 'basic':
            import base64
            creds = '%s:%s' % (self.username or '', self.password or '')
            encoded = base64.b64encode(creds.encode()).decode()
            headers['Authorization'] = 'Basic %s' % encoded
        elif self.auth_type == 'oauth2':
            if self.access_token:
                headers['Authorization'] = 'Bearer %s' % self.access_token
        return headers

    def _get_full_url(self, path):
        base = self.base_url.rstrip('/')
        path = path.lstrip('/')
        return '%s/%s' % (base, path)

    def call_api(self, endpoint_path, http_method='GET', request_data=None, header_extra=None):
        self.ensure_one()
        url = self._get_full_url(endpoint_path)
        headers = self._get_auth_headers()
        if header_extra:
            headers.update(header_extra)

        log_vals = {
            'connection_id': self.id,
            'request_url': url,
            'request_method': http_method,
            'request_headers': json.dumps(headers, indent=2),
            'request_body': json.dumps(request_data, indent=2) if request_data else '',
            'request_datetime': fields.Datetime.now(),
            'status': 'success',
        }

        start = time.time()
        attempt = 0
        last_error = None

        while attempt <= self.max_retries:
            attempt += 1
            try:
                resp = requests.request(
                    method=http_method, url=url, json=request_data,
                    headers=headers, timeout=self.timeout_seconds, verify=self.verify_ssl)
                duration = round(time.time() - start, 3)
                log_vals.update({
                    'duration_seconds': duration,
                    'response_status_code': resp.status_code,
                    'response_headers': json.dumps(dict(resp.headers), indent=2),
                    'response_body': resp.text[:10000],
                    'response_datetime': fields.Datetime.now(),
                    'attempt_number': attempt,
                })
                if resp.ok:
                    log_vals['status'] = 'success' if attempt == 1 else 'retried'
                    self.env['tapis.api.log'].create(log_vals)
                    return resp.json() if resp.text else {}
                log_vals['status'] = 'failed'
                log_vals['error_message'] = 'HTTP %d: %s' % (resp.status_code, resp.text[:500])
                last_error = log_vals['error_message']
            except requests.RequestException as e:
                duration = round(time.time() - start, 3)
                log_vals.update({
                    'duration_seconds': duration,
                    'status': 'failed',
                    'error_message': str(e),
                })
                last_error = str(e)

            if attempt <= self.max_retries:
                _logger.info('Retry %d/%d for %s %s', attempt, self.max_retries, http_method, url)
                time.sleep(self.retry_interval_seconds)
                log_vals['attempt_number'] = attempt
                log_vals['status'] = 'retried'

        self.env['tapis.api.log'].create(log_vals)
        raise UserError(_('API call failed after %d attempts: %s') % (self.max_retries + 1, last_error))
