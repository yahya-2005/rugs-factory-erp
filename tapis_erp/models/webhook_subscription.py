import json
import logging
import hmac
import hashlib
import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

WEBHOOK_EVENTS = [
    ('sale.confirmed', 'Sale Order Confirmed'),
    ('sale.approved', 'Sale Order Approved'),
    ('production.completed', 'Production Completed'),
    ('production.delayed', 'Production Delayed'),
    ('stock.low', 'Stock Below Reorder Point'),
    ('invoice.overdue', 'Invoice Overdue'),
    ('ticket.created', 'Support Ticket Created'),
    ('ticket.resolved', 'Support Ticket Resolved'),
    ('design.analyzed', 'Design AI Analyzed'),
    ('customer.created', 'Customer Created'),
    ('purchase.confirmed', 'Purchase Order Confirmed'),
]


class TapisWebhookSubscription(models.Model):
    _name = 'tapis.webhook.subscription'
    _description = 'Webhook Subscription'
    _inherit = ['tapis.audit.mixin']
    _order = 'name asc'

    name = fields.Char(required=True)
    event_code = fields.Selection(WEBHOOK_EVENTS, string='Event', required=True)
    target_url = fields.Char(required=True, help='URL to send the webhook payload to')
    secret_key = fields.Char(string='Secret Key', help='HMAC secret for payload signing')
    active = fields.Boolean(default=True)
    auth_headers = fields.Text(string='Auth Headers (JSON)',
                                help='Additional headers to include in webhook requests')
    retry_policy = fields.Selection([
        ('none', 'No Retry'),
        ('once', 'Retry Once'),
        ('twice', 'Retry Twice'),
        ('thrice', 'Retry Three Times'),
    ], default='once')

    last_sent = fields.Datetime(readonly=True)
    last_status = fields.Integer(readonly=True)
    total_sent = fields.Integer(default=0, readonly=True)
    success_count = fields.Integer(default=0, readonly=True)
    failure_count = fields.Integer(default=0, readonly=True)

    def send_webhook(self, payload, event_code=None):
        self.ensure_one()
        if not self.active:
            _logger.info('Webhook %s (event: %s) is inactive, skipping', self.name, self.event_code)
            return False

        headers = {'Content-Type': 'application/json'}
        if self.auth_headers:
            try:
                headers.update(json.loads(self.auth_headers))
            except (json.JSONDecodeError, TypeError):
                pass

        body = json.dumps(payload, default=str)
        if self.secret_key:
            signature = hmac.new(self.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers['X-Webhook-Signature'] = signature

        retry_map = {'none': 0, 'once': 1, 'twice': 2, 'thrice': 3}
        max_attempts = retry_map.get(self.retry_policy, 0)

        for attempt in range(max_attempts + 1):
            try:
                resp = requests.post(self.target_url, data=body, headers=headers, timeout=30)
                self.write({
                    'last_sent': fields.Datetime.now(),
                    'last_status': resp.status_code,
                    'total_sent': self.total_sent + 1,
                })
                if resp.ok:
                    self.success_count += 1
                    _logger.info('Webhook %s sent successfully to %s (status %d)',
                                 self.name, self.target_url, resp.status_code)
                    return True
                self.failure_count += 1
                _logger.warning('Webhook %s failed with status %d (attempt %d/%d)',
                                self.name, resp.status_code, attempt + 1, max_attempts + 1)
                if attempt >= max_attempts:
                    return False
            except requests.RequestException as e:
                _logger.error('Webhook %s error: %s (attempt %d/%d)', self.name, e, attempt + 1, max_attempts + 1)
                if attempt >= max_attempts:
                    return False

    @api.model
    def publish_event(self, event_code, payload):
        subs = self.search([('event_code', '=', event_code), ('active', '=', True)])
        for sub in subs:
            try:
                sub.send_webhook(payload, event_code=event_code)
            except Exception as e:
                _logger.error('Webhook publish failed for %s (event: %s): %s', sub.name, event_code, e)
        return len(subs)
