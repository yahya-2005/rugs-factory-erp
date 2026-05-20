import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TapisMobileDevice(models.Model):
    _name = 'tapis.mobile.device'
    _description = 'Mobile Device'
    _inherit = ['tapis.audit.mixin']
    _order = 'last_login_datetime desc'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    device_uuid = fields.Char(string='Device UUID', required=True)
    platform = fields.Selection([
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    ], required=True)
    app_version = fields.Char(string='App Version')
    push_token = fields.Char(string='Push Notification Token')
    last_sync_datetime = fields.Datetime(string='Last Sync')
    last_login_datetime = fields.Datetime(string='Last Login')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    sync_log_ids = fields.One2many('tapis.mobile.sync.log', 'device_id', string='Sync Logs')

    _sql_constraints = [
        ('device_uuid_unique', 'UNIQUE(device_uuid)', 'Device UUID must be unique!'),
    ]

    def action_sync_completed(self):
        self.write({'last_sync_datetime': fields.Datetime.now()})

    @api.model
    def register_device(self, uuid, platform, app_version=None, push_token=None):
        existing = self.search([('device_uuid', '=', uuid)], limit=1)
        if existing:
            existing.write({
                'platform': platform,
                'app_version': app_version or existing.app_version,
                'push_token': push_token or existing.push_token,
                'last_login_datetime': fields.Datetime.now(),
            })
            return existing
        return self.create({
            'name': 'Device %s' % uuid[-8:],
            'user_id': self.env.user.id,
            'device_uuid': uuid,
            'platform': platform,
            'app_version': app_version,
            'push_token': push_token,
            'last_login_datetime': fields.Datetime.now(),
        })

    @api.model
    def send_push_notification(self, title, message, record_model=None, record_id=None, user_ids=None):
        domain = [('active', '=', True)]
        if user_ids:
            domain.append(('user_id', 'in', user_ids))
        devices = self.search(domain)
        count = 0
        for device in devices:
            if device.push_token:
                try:
                    _logger.info('Push notification to device %s: %s - %s', device.name, title, message)
                    count += 1
                except Exception as e:
                    _logger.error('Push notification failed for device %s: %s', device.name, e)
        return count

    @api.model
    def broadcast_notification(self, title, message, record_model=None, record_id=None):
        return self.send_push_notification(title, message, record_model=record_model, record_id=record_id)


class TapisSyncLog(models.Model):
    _name = 'tapis.mobile.sync.log'
    _description = 'Mobile Sync Log'
    _order = 'sync_start_datetime desc'

    device_id = fields.Many2one('tapis.mobile.device', string='Device', required=True, ondelete='cascade')
    sync_start_datetime = fields.Datetime(string='Sync Started', default=fields.Datetime.now, required=True)
    sync_end_datetime = fields.Datetime(string='Sync Ended')
    duration_seconds = fields.Float(string='Duration (s)')
    records_downloaded = fields.Integer(default=0)
    records_uploaded = fields.Integer(default=0)
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], default='success', required=True)
    error_message = fields.Text()
