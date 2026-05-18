import logging
import time
import traceback
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TapisAutomationJob(models.Model):
    _name = 'tapis.automation.job'
    _description = 'Automation Job'
    _inherit = ['tapis.audit.mixin']
    _order = 'name asc'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()

    model_name = fields.Char(required=True)
    method_name = fields.Char(required=True)
    interval_number = fields.Integer(default=1)
    interval_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], default='days')
    next_execution = fields.Datetime()
    last_execution = fields.Datetime()
    last_duration_seconds = fields.Float(readonly=True)
    timeout_seconds = fields.Integer(default=300)

    state = fields.Selection([
        ('idle', 'Idle'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('disabled', 'Disabled'),
    ], compute='_compute_state', store=True, default='idle')

    total_runs = fields.Integer(default=0)
    success_count = fields.Integer(default=0)
    failure_count = fields.Integer(default=0)
    average_duration_seconds = fields.Float(compute='_compute_stats', store=True)
    success_rate = fields.Float(compute='_compute_stats', store=True)

    notify_on_failure = fields.Boolean(default=True)
    notification_user_ids = fields.Many2many('res.users', string='Notify Users')

    ir_cron_id = fields.Many2one('ir.cron', string='Linked Cron', readonly=True, ondelete='set null')

    log_ids = fields.One2many('tapis.automation.job.log', 'job_id', string='Execution Logs')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Job code must be unique!'),
    ]

    @api.depends('active', 'log_ids', 'log_ids.status')
    def _compute_state(self):
        for job in self:
            if not job.active:
                job.state = 'disabled'
                continue
            last_log = self.env['tapis.automation.job.log'].search(
                [('job_id', '=', job.id)], order='id desc', limit=1
            )
            if not last_log:
                job.state = 'idle'
            elif last_log.status == 'running':
                job.state = 'running'
            elif last_log.status == 'success':
                job.state = 'success'
            elif last_log.status == 'failed':
                job.state = 'failed'
            elif last_log.status == 'timeout':
                job.state = 'failed'
            else:
                job.state = 'idle'

    @api.depends('total_runs', 'success_count', 'failure_count', 'log_ids', 'log_ids.duration_seconds')
    def _compute_stats(self):
        for job in self:
            logs = self.env['tapis.automation.job.log'].search([('job_id', '=', job.id)])
            durations = logs.mapped('duration_seconds')
            durations = [d for d in durations if d]
            job.average_duration_seconds = sum(durations) / len(durations) if durations else 0.0
            job.success_rate = round(
                (job.success_count / job.total_runs * 100), 2
            ) if job.total_runs else 0.0

    def action_run_now(self):
        self.ensure_one()
        if self.state == 'running':
            raise UserError(_('Job "%s" is already running.') % self.name)
        _execute_job(self, triggered_by='manual')
        return {'type': 'ir.actions.act_window_close'}

    def action_enable(self):
        self.ensure_one()
        self.active = True
        if self.ir_cron_id:
            self.ir_cron_id.active = True

    def action_disable(self):
        self.ensure_one()
        self.active = False
        if self.ir_cron_id:
            self.ir_cron_id.active = False

    def action_open_logs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Execution Logs - %s') % self.name,
            'res_model': 'tapis.automation.job.log',
            'view_mode': 'tree,form',
            'domain': [('job_id', '=', self.id)],
            'target': 'current',
        }

    def action_sync_ir_cron(self):
        self.ensure_one()
        cron = self.ir_cron_id
        vals = {
            'name': self.name,
            'model_id': self.env['ir.model']._get_id(self.model_name),
            'state': 'code',
            'code': "env['%(model)s'].%(method)s()" % {
                'model': self.model_name,
                'method': self.method_name,
            },
            'interval_number': self.interval_number,
            'interval_type': self.interval_type,
            'numbercall': -1,
            'active': self.active,
        }
        if cron:
            cron.write(vals)
        else:
            cron = self.env['ir.cron'].create(vals)
            self.ir_cron_id = cron

    @api.model
    def cron_monitor(self):
        jobs = self.search([('active', '=', True)])
        for job in jobs:
            if job.next_execution and fields.Datetime.now() >= job.next_execution:
                _execute_job(job, triggered_by='scheduled')

    @api.model
    def _cron_check_overdue_invoices(self):
        _execute_job_code(
            self.env, 'tapis.communication.mixin',
            '_cron_check_overdue_invoices', 'scheduled'
        )

    @api.model
    def _cron_check_low_stock(self):
        _execute_job_code(
            self.env, 'tapis.communication.mixin',
            '_cron_check_low_stock', 'scheduled'
        )

    @api.model
    def _cron_check_document_expiration(self):
        _execute_job_code(
            self.env, 'tapis.communication.mixin',
            '_cron_check_document_expiration', 'scheduled'
        )

    @api.model
    def _cron_check_task_deadlines(self):
        _execute_job_code(
            self.env, 'tapis.communication.mixin',
            '_cron_check_task_deadlines', 'scheduled'
        )

    @api.model
    def _cron_check_maintenance_due(self):
        _execute_job_code(
            self.env, 'tapis.communication.mixin',
            '_cron_check_maintenance_due', 'scheduled'
        )

    @api.model
    def _cron_check_budget_overruns(self):
        _execute_job_code(
            self.env, 'tapis.communication.mixin',
            '_cron_check_budget_overruns', 'scheduled'
        )


def _execute_job(job, triggered_by='scheduled'):
    start = time.time()
    now = fields.Datetime.now()
    log_obj = job.env['tapis.automation.job.log']
    log = log_obj.create({
        'job_id': job.id,
        'start_datetime': now,
        'status': 'running',
        'triggered_by': triggered_by,
        'user_id': job.env.user.id,
    })
    try:
        model = job.env.get(job.model_name)
        if not model:
            raise ValueError(_('Model "%s" not found.') % job.model_name)
        method = getattr(model, job.method_name, None)
        if not method:
            raise ValueError(
                _('Method "%(method)s" not found on model "%(model)s."')
                % {'method': job.method_name, 'model': job.model_name}
            )
        result = method()
        end = time.time()
        duration = round(end - start, 3)
        job.write({
            'last_execution': now,
            'last_duration_seconds': duration,
            'total_runs': job.total_runs + 1,
            'success_count': job.success_count + 1,
        })
        records = result if isinstance(result, int) else 0
        log.write({
            'end_datetime': fields.Datetime.now(),
            'duration_seconds': duration,
            'status': 'success',
            'records_processed': records,
        })
        _update_next_execution(job)
    except Exception as e:
        end = time.time()
        duration = round(end - start, 3)
        tb = traceback.format_exc()
        job.write({
            'last_execution': now,
            'last_duration_seconds': duration,
            'total_runs': job.total_runs + 1,
            'failure_count': job.failure_count + 1,
        })
        log.write({
            'end_datetime': fields.Datetime.now(),
            'duration_seconds': duration,
            'status': 'failed',
            'message': str(e),
            'traceback': tb,
        })
        _logger.error(
            'Automation job "%s" failed: %s\n%s', job.name, e, tb
        )
        if job.notify_on_failure and job.notification_user_ids:
            _send_failure_notification(job, e, tb, duration)
        _update_next_execution(job)


def _execute_job_code(env, model_name, method_name, triggered_by='scheduled'):
    job = env['tapis.automation.job'].search([
        ('model_name', '=', model_name),
        ('method_name', '=', method_name),
    ], limit=1)
    if job:
        _execute_job(job, triggered_by=triggered_by)


def _update_next_execution(job):
    interval_map = {
        'minutes': 'minutes',
        'hours': 'hours',
        'days': 'days',
        'weeks': 'weeks',
        'months': 'months',
    }
    kwargs = {interval_map[job.interval_type]: job.interval_number}
    next_dt = fields.Datetime.now() + timedelta(**kwargs)
    job.next_execution = next_dt


def _send_failure_notification(job, error, tb, duration):
    subject = _('[FAILURE] Automation Job: %s') % job.name
    body = _("""
Job: %(name)s
Error: %(error)s
Duration: %(duration).2f seconds
Time: %(time)s

Traceback:
%(traceback)s
""") % {
        'name': job.name,
        'error': str(error),
        'duration': duration,
        'time': fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'traceback': tb,
    }
    for user in job.notification_user_ids:
        job.env['mail.activity'].create({
            'activity_type_id': job.env.ref('mail.mail_activity_data_warning').id,
            'summary': subject,
            'note': body,
            'user_id': user.id,
            'res_model_id': job.env['ir.model']._get_id('tapis.automation.job'),
            'res_id': job.id,
        })
