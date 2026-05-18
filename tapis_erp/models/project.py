from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisProject(models.Model):
    _name = 'tapis.project'
    _description = 'Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Project Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, readonly=True, default=lambda s: _('New'))
    description = fields.Html(string='Description')

    manager_id = fields.Many2one('tapis.employee', string='Project Manager', tracking=True)
    customer_id = fields.Many2one('tapis.customer', string='Customer')

    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)

    planned_hours = fields.Float(string='Planned Hours', default=0.0)
    actual_hours = fields.Float(string='Actual Hours', compute='_compute_project_totals', store=True)
    progress_percent = fields.Float(string='Progress (%)', compute='_compute_project_totals', store=True)

    budget_amount = fields.Float(string='Budget (MAD)', default=0.0)
    actual_cost = fields.Float(string='Actual Cost (MAD)', compute='_compute_project_totals', store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='medium', tracking=True)

    tag_ids = fields.Many2many('tapis.project.tag', string='Tags')

    task_ids = fields.One2many('tapis.task', 'project_id', string='Tasks')
    task_count = fields.Integer(string='Task Count', compute='_compute_project_totals', store=True)

    active = fields.Boolean(string='Active', default=True)
    note = fields.Text(string='Notes')
    document_count = fields.Integer(compute='_compute_document_count')

    @api.depends('task_ids', 'task_ids.actual_hours', 'task_ids.progress_percent', 'task_ids.state',
                 'task_ids.assigned_employee_id')
    def _compute_project_totals(self):
        for rec in self:
            tasks = rec.task_ids
            rec.task_count = len(tasks)
            rec.actual_hours = sum(tasks.mapped('actual_hours'))

            if tasks:
                rec.progress_percent = sum(tasks.mapped('progress_percent')) / len(tasks)
            else:
                rec.progress_percent = 0.0

            total_cost = 0.0
            for task in tasks:
                employee = task.assigned_employee_id
                rate = employee.hourly_rate if employee and employee.hourly_rate else 0.0
                total_cost += task.actual_hours * rate
            rec.actual_cost = total_cost

    def action_start(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'in_progress'
                rec.message_post(body=_('Project started.'))

    def action_put_on_hold(self):
        for rec in self:
            if rec.state == 'in_progress':
                rec.state = 'on_hold'
                rec.message_post(body=_('Project put on hold.'))

    def action_mark_done(self):
        for rec in self:
            rec.state = 'done'
            rec.message_post(body=_('Project marked as done.'))

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_('Completed projects cannot be cancelled.'))
            rec.state = 'cancelled'
            rec.message_post(body=_('Project cancelled.'))

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tasks',
            'res_model': 'tapis.task',
            'view_mode': 'kanban,tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tapis.project.code') or _('New')
        return super().create(vals)

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('project_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
            'target': 'current',
        }


class TapisProjectTag(models.Model):
    _name = 'tapis.project.tag'
    _description = 'Project Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color', default=0)
