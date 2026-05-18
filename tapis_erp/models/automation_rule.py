import logging
import time
import traceback
import json
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval as safe_eval_

_logger = logging.getLogger(__name__)

SUPPORTED_MODELS = [
    ('tapis.sale', 'Sales Order'),
    ('tapis.production', 'Production Order'),
    ('tapis.inventory.optimization', 'Inventory Optimization'),
    ('tapis.support.ticket', 'Support Ticket'),
    ('tapis.customer', 'Customer'),
    ('tapis.invoice', 'Invoice'),
    ('tapis.purchase', 'Purchase Order'),
    ('tapis.project', 'Project'),
    ('tapis.task', 'Task'),
]

TRIGGER_TYPES = [
    ('on_create', 'On Create'),
    ('on_write', 'On Update'),
    ('on_delete', 'On Delete'),
    ('on_state_change', 'On State Change'),
    ('scheduled', 'Scheduled'),
    ('manual', 'Manual'),
]

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

INTERVAL_TYPES = [
    ('minutes', 'Minutes'),
    ('hours', 'Hours'),
    ('days', 'Days'),
    ('weeks', 'Weeks'),
    ('months', 'Months'),
]


class TapisAutomationRule(models.Model):
    _name = 'tapis.automation.rule'
    _description = 'Automation Rule'
    _inherit = ['tapis.audit.mixin']
    _order = 'sequence, name asc'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    trigger_type = fields.Selection(TRIGGER_TYPES, string='Trigger Type', required=True, default='manual')
    model_name = fields.Selection(
        SUPPORTED_MODELS, string='Target Model', required=True,
        help='Model this rule applies to')
    trigger_field = fields.Char(string='Trigger Field',
                                help="Field name to monitor (e.g. 'state' for on_state_change)")
    trigger_value = fields.Char(string='Trigger Value',
                                help="Expected field value (e.g. 'done' for on_state_change)")

    domain_expression = fields.Text(string='Domain Condition',
                                    help="Odoo domain expression, e.g. [('state','=','draft')]\n"
                                         "Leave empty to match all records.")
    python_condition = fields.Text(string='Python Condition',
                                   help="Python expression using 'record' and 'env' variables.\n"
                                        "Must evaluate to True/False.\n"
                                        "Leave empty to always pass.")

    sequence = fields.Integer(default=10)
    stop_on_error = fields.Boolean(default=True, help='Stop execution of subsequent actions if one fails')
    max_retries = fields.Integer(default=3, help='Maximum retry attempts on failure')
    retry_interval_minutes = fields.Integer(default=10, help='Minutes between retry attempts')

    cron_interval_number = fields.Integer(string='Cron Interval', default=1)
    cron_interval_type = fields.Selection(INTERVAL_TYPES, string='Cron Interval Type', default='days')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('archived', 'Archived'),
    ], default='draft', required=True)

    action_line_ids = fields.One2many('tapis.automation.action', 'rule_id', string='Actions',
                                       copy=True)
    execution_log_ids = fields.One2many('tapis.automation.execution.log', 'rule_id',
                                         string='Execution Logs')

    ir_cron_id = fields.Many2one('ir.cron', string='Linked Cron Job', readonly=True, ondelete='set null')

    execution_count = fields.Integer(compute='_compute_metrics', store=True)
    success_count = fields.Integer(compute='_compute_metrics', store=True)
    failure_count = fields.Integer(compute='_compute_metrics', store=True)
    success_rate = fields.Float(compute='_compute_metrics', store=True)
    average_duration = fields.Float(string='Avg Duration (s)', compute='_compute_metrics', store=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Rule code must be unique!'),
    ]

    @api.depends('execution_log_ids', 'execution_log_ids.status', 'execution_log_ids.duration_seconds')
    def _compute_metrics(self):
        for rule in self:
            logs = self.env['tapis.automation.execution.log'].search([('rule_id', '=', rule.id)])
            total = len(logs)
            successes = len(logs.filtered(lambda l: l.status == 'success'))
            failures = len(logs.filtered(lambda l: l.status == 'failed'))
            durations = logs.mapped('duration_seconds')
            durations = [d for d in durations if d]
            rule.execution_count = total
            rule.success_count = successes
            rule.failure_count = failures
            rule.success_rate = round(successes / total * 100, 2) if total else 0.0
            rule.average_duration = round(sum(durations) / len(durations), 2) if durations else 0.0

    def action_activate(self):
        for rule in self:
            if rule.state == 'draft' or rule.state == 'paused':
                rule.state = 'active'
                if rule.trigger_type == 'scheduled':
                    rule._create_ir_cron()
        if not self._context.get('no_reload'):
            return {'type': 'ir.actions.act_window_close'}

    def action_pause(self):
        for rule in self:
            rule.state = 'paused'
            if rule.ir_cron_id:
                rule.ir_cron_id.active = False
        if not self._context.get('no_reload'):
            return {'type': 'ir.actions.act_window_close'}

    def action_archive(self):
        for rule in self:
            rule.state = 'archived'
            rule.active = False
            if rule.ir_cron_id:
                rule.ir_cron_id.active = False
        if not self._context.get('no_reload'):
            return {'type': 'ir.actions.act_window_close'}

    def action_reset_to_draft(self):
        for rule in self:
            rule.state = 'draft'
            rule.active = True
            if rule.ir_cron_id:
                rule.ir_cron_id.active = False
        if not self._context.get('no_reload'):
            return {'type': 'ir.actions.act_window_close'}

    def action_run_now(self):
        self.ensure_one()
        if self.state != 'active' and self.state != 'draft':
            raise UserError(_('Rule must be active or in draft to run manually.'))
        self.execute_rule(None, triggered_by='manual')
        return {'type': 'ir.actions.act_window_close'}

    def execute_rule(self, record=None, triggered_by='on_write'):
        self.ensure_one()
        if self.state not in ('active', 'draft'):
            _logger.warning('Rule %s is not active (state=%s)', self.code, self.state)
            return False

        start = time.time()
        log_obj = self.env['tapis.automation.execution.log']
        log = log_obj.create({
            'rule_id': self.id,
            'model_name': self.model_name,
            'record_id': record.id if record else 0,
            'execution_datetime': fields.Datetime.now(),
            'status': 'success',
            'attempt_number': 1,
        })

        try:
            if record and not self.evaluate_conditions(record):
                log.write({'status': 'skipped', 'result_message': 'Conditions not met'})
                return False

            self.execute_actions(record)
            duration = round(time.time() - start, 3)
            log.write({
                'status': 'success',
                'duration_seconds': duration,
                'result_message': 'All actions executed successfully',
            })
            return True

        except Exception as e:
            duration = round(time.time() - start, 3)
            tb = traceback.format_exc()
            log.write({
                'status': 'failed',
                'duration_seconds': duration,
                'result_message': str(e),
                'error_traceback': tb,
            })
            _logger.error('Rule %s failed: %s\n%s', self.code, e, tb)
            self._handle_retry(record, triggered_by, log)
            return False

    def evaluate_conditions(self, record):
        self.ensure_one()
        domain_ok = True
        if self.domain_expression:
            try:
                domain = safe_eval_(self.domain_expression, {'__builtins__': {}})
                if not isinstance(domain, (list, tuple)):
                    domain = []
                domain_ok = record.filtered_domain(domain).filtered(lambda r: r.id == record.id)
                if isinstance(domain_ok, models.BaseModel):
                    domain_ok = bool(domain_ok)
            except Exception as e:
                _logger.warning('Domain evaluation failed for rule %s: %s', self.code, e)
                domain_ok = False

        python_ok = True
        if self.python_condition:
            try:
                locals_dict = {
                    'record': record,
                    'env': self.env,
                    'user': self.env.user,
                    'context': self._context,
                    'datetime': datetime,
                    'timedelta': timedelta,
                    'fields': fields,
                }
                result = safe_eval_(self.python_condition, {'__builtins__': {}}, locals_dict)
                python_ok = bool(result)
            except Exception as e:
                _logger.warning('Python condition failed for rule %s: %s', self.code, e)
                python_ok = False

        return domain_ok and python_ok

    def execute_actions(self, record):
        self.ensure_one()
        actions = self.action_line_ids.sorted('sequence')
        for action in actions:
            try:
                action.execute_action(record)
            except Exception as e:
                _logger.error('Action %d on rule %s failed: %s', action.sequence, self.code, e)
                if self.stop_on_error and not action.continue_on_error:
                    raise
                if action.continue_on_error:
                    continue
                raise
        return True

    def _handle_retry(self, record, triggered_by, failed_log):
        if not self.max_retries:
            return
        attempt = 1
        while attempt < self.max_retries:
            attempt += 1
            _logger.info('Retry attempt %d/%d for rule %s', attempt, self.max_retries, self.code)
            time.sleep(1)
            start = time.time()
            retry_log = self.env['tapis.automation.execution.log'].create({
                'rule_id': self.id,
                'model_name': self.model_name,
                'record_id': record.id if record else 0,
                'execution_datetime': fields.Datetime.now(),
                'status': 'retried',
                'attempt_number': attempt,
            })
            try:
                if record and not self.evaluate_conditions(record):
                    retry_log.write({'status': 'skipped', 'result_message': 'Conditions not met on retry'})
                    continue
                self.execute_actions(record)
                duration = round(time.time() - start, 3)
                retry_log.write({
                    'status': 'success',
                    'duration_seconds': duration,
                    'result_message': 'Retry succeeded',
                })
                return
            except Exception as e:
                duration = round(time.time() - start, 3)
                tb = traceback.format_exc()
                retry_log.write({
                    'status': 'failed',
                    'duration_seconds': duration,
                    'result_message': str(e),
                    'error_traceback': tb,
                })
                _logger.error('Retry %d for rule %s failed: %s', attempt, self.code, e)

    def _create_ir_cron(self):
        self.ensure_one()
        cron = self.ir_cron_id
        vals = {
            'name': self.name,
            'model_id': self.env['ir.model']._get_id('tapis.automation.rule'),
            'state': 'code',
            'code': "env['tapis.automation.rule'].browse(%d).execute_scheduled()" % self.id,
            'interval_number': self.cron_interval_number,
            'interval_type': self.cron_interval_type,
            'numbercall': -1,
            'active': self.state == 'active',
        }
        if cron:
            cron.write(vals)
        else:
            cron = self.env['ir.cron'].create(vals)
            self.ir_cron_id = cron

    def execute_scheduled(self):
        rules = self.search([('state', '=', 'active'), ('trigger_type', '=', 'scheduled')])
        for rule in rules:
            _logger.info('Executing scheduled rule: %s', rule.code)
            try:
                model = self.env.get(rule.model_name)
                if not model:
                    _logger.warning('Model %s not found for rule %s', rule.model_name, rule.code)
                    continue
                domain = []
                if rule.domain_expression:
                    try:
                        domain = safe_eval_(rule.domain_expression, {'__builtins__': {}})
                    except Exception:
                        domain = []
                records = model.search(domain)
                for rec in records:
                    rule.execute_rule(record=rec, triggered_by='scheduled')
            except Exception as e:
                _logger.error('Scheduled rule %s execution failed: %s', rule.code, e)

    @api.model
    def check_trigger_on_create(self, records):
        model_name = records._name
        rules = self.search([
            ('state', '=', 'active'),
            ('model_name', '=', model_name),
            ('trigger_type', 'in', ['on_create', 'on_state_change']),
        ])
        for rec in records:
            for rule in rules:
                if rule.trigger_type == 'on_create':
                    rule.execute_rule(record=rec, triggered_by='on_create')
                elif rule.trigger_type == 'on_state_change' and rule.trigger_field:
                    old_val = rec._origin[rule.trigger_field] if hasattr(rec, '_origin') and rec._origin else None
                    new_val = rec[rule.trigger_field]
                    if rule.trigger_value and str(new_val) == rule.trigger_value:
                        rule.execute_rule(record=rec, triggered_by='on_state_change')
                    elif not rule.trigger_value and old_val != new_val:
                        rule.execute_rule(record=rec, triggered_by='on_state_change')

    @api.model
    def check_trigger_on_write(self, records):
        model_name = records._name
        rules = self.search([
            ('state', '=', 'active'),
            ('model_name', '=', model_name),
            ('trigger_type', 'in', ['on_write', 'on_state_change']),
        ])
        for rec in records:
            for rule in rules:
                if rule.trigger_type == 'on_write':
                    rule.execute_rule(record=rec, triggered_by='on_write')
                elif rule.trigger_type == 'on_state_change' and rule.trigger_field:
                    old_val = rec._origin[rule.trigger_field] if hasattr(rec, '_origin') and rec._origin else None
                    new_val = rec[rule.trigger_field]
                    if old_val != new_val:
                        if not rule.trigger_value or str(new_val) == rule.trigger_value:
                            rule.execute_rule(record=rec, triggered_by='on_state_change')

    @api.model
    def check_trigger_on_delete(self, records):
        model_name = records._name
        rules = self.search([
            ('state', '=', 'active'),
            ('model_name', '=', model_name),
            ('trigger_type', '=', 'on_delete'),
        ])
        for rec in records:
            for rule in rules:
                rule.execute_rule(record=rec, triggered_by='on_delete')

    def action_open_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Execution Logs - %s') % self.name,
            'res_model': 'tapis.automation.execution.log',
            'view_mode': 'tree,form',
            'domain': [('rule_id', '=', self.id)],
            'target': 'current',
        }


class TapisAutomationMixin(models.AbstractModel):
    _name = 'tapis.automation.mixin'
    _description = 'Automation Mixin'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        try:
            self.env['tapis.automation.rule'].check_trigger_on_create(records)
        except Exception:
            _logger.exception('Automation trigger check on create failed')
        return records

    def write(self, vals):
        result = super().write(vals)
        try:
            self.env['tapis.automation.rule'].check_trigger_on_write(self)
        except Exception:
            _logger.exception('Automation trigger check on write failed')
        return result

    def unlink(self):
        try:
            self.env['tapis.automation.rule'].check_trigger_on_delete(self)
        except Exception:
            _logger.exception('Automation trigger check on unlink failed')
        return super().unlink()
