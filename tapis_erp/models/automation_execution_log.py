import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class TapisAutomationExecutionLog(models.Model):
    _name = 'tapis.automation.execution.log'
    _description = 'Automation Execution Log'
    _order = 'execution_datetime desc'

    rule_id = fields.Many2one('tapis.automation.rule', string='Rule', required=True, ondelete='cascade')
    action_id = fields.Many2one('tapis.automation.action', string='Action', ondelete='set null')

    model_name = fields.Char(string='Model')
    record_id = fields.Integer(string='Record ID')
    record_ref = fields.Reference(
        selection='_selection_model_ref',
        string='Record',
        compute='_compute_record_ref',
        store=False,
    )

    execution_datetime = fields.Datetime(string='Execution Time', default=fields.Datetime.now, required=True)
    duration_seconds = fields.Float(string='Duration (s)')
    status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retried', 'Retried'),
        ('skipped', 'Skipped'),
    ], string='Status', default='success', required=True)
    attempt_number = fields.Integer(string='Attempt', default=1)
    result_message = fields.Text(string='Result Message')
    error_traceback = fields.Text(string='Error Traceback')

    triggered_by = fields.Selection([
        ('on_create', 'On Create'),
        ('on_write', 'On Update'),
        ('on_delete', 'On Delete'),
        ('on_state_change', 'On State Change'),
        ('scheduled', 'Scheduled'),
        ('manual', 'Manual'),
    ], string='Triggered By')

    def _selection_model_ref(self):
        models_list = [
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
        return models_list

    @api.depends('model_name', 'record_id')
    def _compute_record_ref(self):
        for log in self:
            if log.model_name and log.record_id:
                model = self.env.get(log.model_name)
                if model:
                    rec = model.browse(log.record_id)
                    if rec.exists():
                        log.record_ref = '%s,%d' % (log.model_name, log.record_id)
                        continue
            log.record_ref = None

    def action_view_record(self):
        self.ensure_one()
        if not self.model_name or not self.record_id:
            raise ValueError(_('No record reference available.'))
        model = self.env.get(self.model_name)
        if not model:
            raise ValueError(_('Model %s not found.') % self.model_name)
        rec = model.browse(self.record_id)
        if not rec.exists():
            raise ValueError(_('Record not found (ID: %d).') % self.record_id)
        return {
            'type': 'ir.actions.act_window',
            'name': rec.display_name or _('Record'),
            'res_model': self.model_name,
            'res_id': self.record_id,
            'view_mode': 'form',
            'target': 'current',
        }
