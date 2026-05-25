import logging
import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TapisDwConfig(models.Model):
    _name = 'tapis.dw.config'
    _description = 'Data Warehouse Configuration'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, unique=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    incremental_load = fields.Boolean(default=True)
    last_etl_datetime = fields.Datetime()
    retention_months = fields.Integer(default=60)

    auto_run = fields.Boolean(default=True)
    cron_interval_number = fields.Integer(default=1)
    cron_interval_type = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], default='days')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
    ], default='draft')

    etl_run_ids = fields.One2many('tapis.etl.run', 'config_id', string='ETL Runs')
    etl_run_count = fields.Integer(compute='_compute_etl_run_count')
    last_run_id = fields.Many2one('tapis.etl.run', compute='_compute_last_run')
    last_run_status = fields.Selection(related='last_run_id.status')
    last_run_duration = fields.Float(related='last_run_id.duration_seconds')
    data_freshness = fields.Char(compute='_compute_data_freshness')

    rows_in_warehouse = fields.Integer(compute='_compute_warehouse_stats')
    largest_fact_table = fields.Char(compute='_compute_warehouse_stats')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Warehouse configuration code must be unique!'),
    ]

    def _compute_etl_run_count(self):
        for rec in self:
            rec.etl_run_count = len(rec.etl_run_ids)

    def _compute_last_run(self):
        for rec in self:
            rec.last_run_id = rec.etl_run_ids.search([('config_id', '=', rec.id)], limit=1) if rec.etl_run_ids else False

    def _compute_data_freshness(self):
        for rec in self:
            if rec.last_etl_datetime:
                delta = fields.Datetime.now() - rec.last_etl_datetime
                hours = delta.total_seconds() // 3600
                if hours < 1:
                    rec.data_freshness = _('Less than 1 hour ago')
                elif hours < 24:
                    rec.data_freshness = _('%d hours ago') % hours
                else:
                    rec.data_freshness = _('%d days ago') % (hours // 24)
            else:
                rec.data_freshness = _('Never')

    def _compute_warehouse_stats(self):
        for rec in self:
            total = 0
            largest = ''
            largest_count = 0
            fact_models = [
                'tapis.dw.fact_sales',
                'tapis.dw.fact_inventory',
                'tapis.dw.fact_production',
                'tapis.dw.fact_finance',
                'tapis.dw.fact_quality',
                'tapis.dw.fact_support',
            ]
            for model in fact_models:
                try:
                    cnt = self.env[model].search_count([])
                    total += cnt
                    if cnt > largest_count:
                        largest_count = cnt
                        largest = model
                except Exception:
                    pass
            rec.rows_in_warehouse = total
            rec.largest_fact_table = largest

    def action_run_etl(self):
        self.ensure_one()
        if self.state == 'paused':
            raise UserError(_('Cannot run ETL on a paused configuration.'))
        self.state = 'active'
        etl_run = self.env['tapis.etl.run'].create({
            'config_id': self.id,
            'start_datetime': fields.Datetime.now(),
            'status': 'success',
        })
        try:
            etl_run._execute_extract()
            etl_run._execute_transform()
            etl_run._execute_load()
            etl_run._finalize_success()
            self.last_etl_datetime = fields.Datetime.now()
        except Exception as e:
            etl_run._finalize_failed(str(e))
            _logger.exception('ETL run failed for config %s', self.name)
            raise UserError(_('ETL run failed: %s') % str(e))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tapis.etl.run',
            'res_id': etl_run.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_rebuild_warehouse(self):
        self.ensure_one()
        for model in ['tapis.dw.fact_sales', 'tapis.dw.fact_inventory',
                       'tapis.dw.fact_production', 'tapis.dw.fact_finance',
                       'tapis.dw.fact_quality', 'tapis.dw.fact_support',
                       'tapis.dw.dim_date', 'tapis.dw.dim_product',
                       'tapis.dw.dim_customer', 'tapis.dw.dim_company',
                       'tapis.dw.dim_supplier', 'tapis.dw.dim_user',
                       'tapis.dw.dim_resource']:
            try:
                self.env[model].sudo().search([]).unlink()
            except Exception:
                pass
        self.last_etl_datetime = False
        return self.action_run_etl()

    def action_export_csv(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/dw/export/csv?config_id=%d' % self.id,
            'target': 'self',
        }

    def action_export_excel(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/dw/export/excel?config_id=%d' % self.id,
            'target': 'self',
        }

    @api.model
    def cron_run_etl(self):
        configs = self.search([('auto_run', '=', True), ('state', '=', 'active')])
        for config in configs:
            try:
                config.action_run_etl()
            except Exception as e:
                _logger.error('Cron ETL failed for %s: %s', config.name, e)
        return True


class TapisEtlRun(models.Model):
    _name = 'tapis.etl.run'
    _description = 'ETL Execution Run'
    _order = 'start_datetime desc'

    config_id = fields.Many2one('tapis.dw.config', string='Warehouse Config', required=True, ondelete='cascade')
    start_datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    end_datetime = fields.Datetime()
    duration_seconds = fields.Float(compute='_compute_duration', store=True)
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ], default='success')
    rows_extracted = fields.Integer(default=0)
    rows_transformed = fields.Integer(default=0)
    rows_loaded = fields.Integer(default=0)
    error_message = fields.Text()

    def _compute_duration(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                delta = rec.end_datetime - rec.start_datetime
                rec.duration_seconds = delta.total_seconds()
            else:
                rec.duration_seconds = 0.0

    def _execute_extract(self):
        FactEngine = self.env['tapis.dw.fact.engine']
        extracted = FactEngine.extract_data()
        self.rows_extracted = extracted
        return extracted

    def _execute_transform(self):
        FactEngine = self.env['tapis.dw.fact.engine']
        transformed = FactEngine.transform_data()
        self.rows_transformed = transformed
        return transformed

    def _execute_load(self):
        FactEngine = self.env['tapis.dw.fact.engine']
        loaded = FactEngine.load_dimensions()
        loaded += FactEngine.load_facts()
        self.rows_loaded = loaded
        return loaded

    def _finalize_success(self):
        self.write({
            'end_datetime': fields.Datetime.now(),
            'status': 'success',
        })
        self._compute_duration()

    def _finalize_failed(self, error_msg):
        self.write({
            'end_datetime': fields.Datetime.now(),
            'status': 'failed',
            'error_message': error_msg,
        })
        self._compute_duration()
