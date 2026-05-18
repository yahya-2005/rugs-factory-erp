import logging
import json
import traceback

from odoo import _, api, fields, models
from odoo.tools.safe_eval import safe_eval as safe_eval_
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

ACTION_TYPES = [
    ('send_email', 'Send Email'),
    ('create_activity', 'Create Activity'),
    ('create_record', 'Create Record'),
    ('update_record', 'Update Record'),
    ('send_notification', 'Internal Notification'),
    ('execute_python', 'Execute Python Code'),
    ('generate_report', 'Generate PDF Report'),
    ('webhook', 'Call External Webhook'),
]


class TapisAutomationAction(models.Model):
    _name = 'tapis.automation.action'
    _description = 'Automation Action'
    _order = 'sequence'

    rule_id = fields.Many2one('tapis.automation.rule', string='Rule', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    action_type = fields.Selection(ACTION_TYPES, string='Action Type', required=True)

    target_model = fields.Selection(
        related='rule_id.model_name',
        string='Target Model',
        readonly=True,
    )
    values_expression = fields.Text(
        string='Values Expression',
        help="Python dict expression for create/update values.\n"
             "Variables: record, env, user, context, datetime, timedelta\n"
             "Example: {'name': record.name + ' - Auto', 'state': 'draft'}"
    )

    email_template_id = fields.Many2one('mail.template', string='Email Template')
    activity_type_id = fields.Many2one('mail.activity.type', string='Activity Type')
    activity_summary = fields.Char(string='Activity Summary')
    activity_note = fields.Text(string='Activity Note')
    activity_user_id = fields.Many2one('res.users', string='Assign Activity To')

    server_action_id = fields.Many2one('ir.actions.server', string='Server Action')

    webhook_url = fields.Char(string='Webhook URL', help='URL to call via HTTP POST')
    webhook_headers = fields.Text(string='Webhook Headers (JSON)',
                                  help='JSON dict of custom headers')
    webhook_body = fields.Text(string='Webhook Body Expression',
                               help="Python expression returning dict for JSON body.\n"
                                    "Variables: record, env, user, context")

    python_code = fields.Text(string='Python Code',
                              help="Python code to execute.\n"
                                   "Variables: record, env, user, context\n"
                                   "Use safe_eval compatible syntax.")

    report_template_id = fields.Many2one('ir.actions.report', string='Report Template')
    report_save_as_document = fields.Boolean(string='Save Report as Document', default=False)

    notification_user_ids = fields.Many2many('res.users', string='Notify Users')
    notification_subject = fields.Char(string='Notification Subject')
    notification_body = fields.Text(string='Notification Body')

    continue_on_error = fields.Boolean(default=False,
                                       help="Continue with next actions even if this one fails")

    def execute_action(self, record=None):
        self.ensure_one()
        _logger.info('Executing action %s (type=%s) for rule %s',
                     self.sequence, self.action_type, self.rule_id.code)

        method_map = {
            'send_email': '_execute_send_email',
            'create_activity': '_execute_create_activity',
            'create_record': '_execute_create_record',
            'update_record': '_execute_update_record',
            'send_notification': '_execute_send_notification',
            'execute_python': '_execute_python_code',
            'generate_report': '_execute_generate_report',
            'webhook': '_execute_webhook',
        }

        method_name = method_map.get(self.action_type)
        if not method_name:
            raise ValueError(_('Unknown action type: %s') % self.action_type)

        method = getattr(self, method_name, None)
        if not method:
            raise ValueError(_('Action method not implemented: %s') % method_name)

        return method(record)

    def _get_eval_context(self, record=None):
        return {
            'record': record,
            'env': self.env,
            'user': self.env.user,
            'context': self._context,
            'datetime': datetime,
            'timedelta': timedelta,
            'fields': fields,
            'json': json,
        }

    def _safe_eval_value(self, expression, record=None):
        if not expression:
            return {}
        ctx = self._get_eval_context(record)
        result = safe_eval_(expression, {'__builtins__': {}}, ctx)
        return result

    def _execute_send_email(self, record=None):
        if not self.email_template_id:
            raise UserError(_('Email template is required for send_email action.'))
        if record and hasattr(record, '_name'):
            self.email_template_id.send_mail(record.id, force_send=True)
        return True

    def _execute_create_activity(self, record=None):
        if not self.activity_type_id:
            raise UserError(_('Activity type is required for create_activity action.'))
        if not record:
            raise UserError(_('Record is required for create_activity action.'))
        vals = {
            'activity_type_id': self.activity_type_id.id,
            'summary': self.activity_summary or _('Automation Activity'),
            'note': self.activity_note or '',
            'user_id': self.activity_user_id.id if self.activity_user_id else self.env.user.id,
            'res_model_id': self.env['ir.model']._get_id(record._name),
            'res_id': record.id,
        }
        self.env['mail.activity'].create(vals)
        return True

    def _execute_create_record(self, record=None):
        if not self.target_model:
            raise UserError(_('Target model is required for create_record action.'))
        model = self.env.get(self.target_model)
        if not model:
            raise ValueError(_('Model %s not found.') % self.target_model)
        values = {}
        if self.values_expression:
            values = self._safe_eval_value(self.values_expression, record)
        if not values:
            raise UserError(_('Values expression must return a non-empty dict.'))
        if isinstance(values, dict):
            model.create(values)
        return True

    def _execute_update_record(self, record=None):
        if not record:
            raise UserError(_('Record is required for update_record action.'))
        values = {}
        if self.values_expression:
            values = self._safe_eval_value(self.values_expression, record)
        if not values:
            raise UserError(_('Values expression must return a non-empty dict for update.'))
        if isinstance(values, dict):
            record.write(values)
        return True

    def _execute_send_notification(self, record=None):
        users = self.notification_user_ids
        if not users:
            users = self.env.user
        subject = self.notification_subject or _('Automation Notification: %s') % self.rule_id.name
        body = self.notification_body or _('Action executed by automation rule: %s') % self.rule_id.name
        for user in users:
            self.env['mail.activity'].create({
                'activity_type_id': self.env.ref('mail.mail_activity_data_warning').id,
                'summary': subject,
                'note': body,
                'user_id': user.id,
                'res_model_id': self.env['ir.model']._get_id(self.rule_id._name),
                'res_id': self.rule_id.id,
            })
        return True

    def _execute_python_code(self, record=None):
        if not self.python_code:
            raise UserError(_('Python code is required for execute_python action.'))
        ctx = self._get_eval_context(record)
        safe_eval_(self.python_code, {'__builtins__': {}}, ctx)
        return True

    def _execute_generate_report(self, record=None):
        if not self.report_template_id:
            raise UserError(_('Report template is required for generate_report action.'))
        if not record:
            raise UserError(_('Record is required for generate_report action.'))
        self.report_template_id._render(record.ids)
        return True

    def _execute_webhook(self, record=None):
        import urllib.request
        import urllib.error

        if not self.webhook_url:
            raise UserError(_('Webhook URL is required for webhook action.'))
        headers = {'Content-Type': 'application/json'}
        if self.webhook_headers:
            extra_headers = safe_eval_(self.webhook_headers, {'__builtins__': {}})
            if isinstance(extra_headers, dict):
                headers.update(extra_headers)
        body_data = {}
        if self.webhook_body:
            body_data = self._safe_eval_value(self.webhook_body, record)
        data = json.dumps(body_data).encode('utf-8')
        req = urllib.request.Request(self.webhook_url, data=data, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                _logger.info('Webhook %s responded with status %d', self.webhook_url, resp.status)
        except urllib.error.URLError as e:
            _logger.error('Webhook %s failed: %s', self.webhook_url, e)
            raise
        return True
