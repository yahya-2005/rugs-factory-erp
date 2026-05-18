from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisTask(models.Model):
    _name = 'tapis.task'
    _description = 'Task'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.communication.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Task Title', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, readonly=True, default=lambda s: _('New'))
    project_id = fields.Many2one('tapis.project', string='Project', required=True, tracking=True)
    description = fields.Html(string='Description')

    assigned_employee_id = fields.Many2one('tapis.employee', string='Assigned To', tracking=True)

    related_design_id = fields.Many2one('tapis.design', string='Related Design')
    related_production_id = fields.Many2one('tapis.production', string='Related Production')
    related_sale_id = fields.Many2one('tapis.sale', string='Related Sale Order')

    start_date = fields.Date(string='Start Date')
    deadline = fields.Date(string='Deadline', tracking=True)

    planned_hours = fields.Float(string='Planned Hours', default=0.0)
    actual_hours = fields.Float(string='Actual Hours', compute='_compute_task_totals', store=True)
    progress_percent = fields.Float(string='Progress (%)', default=0.0)

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='medium', tracking=True)

    state = fields.Selection([
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Review'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='todo', required=True, tracking=True)

    tag_ids = fields.Many2many('tapis.project.tag', string='Tags')

    timesheet_ids = fields.One2many('tapis.task.timesheet', 'task_id', string='Timesheets')
    timesheet_count = fields.Integer(string='Timesheet Count', compute='_compute_task_totals', store=True)

    note = fields.Text(string='Notes')

    @api.depends('timesheet_ids', 'timesheet_ids.hours')
    def _compute_task_totals(self):
        for rec in self:
            rec.actual_hours = sum(rec.timesheet_ids.mapped('hours'))
            rec.timesheet_count = len(rec.timesheet_ids)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for rec in self:
            if rec.project_id:
                rec.assigned_employee_id = rec.project_id.manager_id

    def action_start(self):
        for rec in self:
            if rec.state != 'todo':
                raise UserError(_('Only todo tasks can be started.'))
            rec.state = 'in_progress'
            rec.start_date = fields.Date.today()
            rec.message_post(body=_('Task started.'))

    def action_submit_review(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_('Only in-progress tasks can be submitted for review.'))
            rec.state = 'review'
            rec.message_post(body=_('Task submitted for review.'))

    def action_mark_done(self):
        for rec in self:
            if rec.state not in ('review', 'in_progress'):
                raise UserError(_('Task must be in review or in progress to mark done.'))
            rec.state = 'done'
            rec.progress_percent = 100.0
            rec.message_post(body=_('Task completed.'))

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_('Completed tasks cannot be cancelled.'))
            rec.state = 'cancelled'
            rec.message_post(body=_('Task cancelled.'))

    def action_view_timesheets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Timesheets',
            'res_model': 'tapis.task.timesheet',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
            'context': {'default_task_id': self.id},
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tapis.task.code') or _('New')
        return super().create(vals)
