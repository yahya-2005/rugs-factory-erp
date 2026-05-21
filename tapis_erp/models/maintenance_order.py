from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisMaintenanceOrder(models.Model):
    _name = 'tapis.maintenance.order'
    _description = 'Maintenance Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.communication.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(string='Order Reference', required=True, readonly=True,
                       default=lambda s: _('New'))
    equipment_id = fields.Many2one(
        'tapis.equipment', string='Equipment',
        required=True, tracking=True
    )
    maintenance_type = fields.Selection([
        ('preventive', 'Preventive'),
        ('corrective', 'Corrective'),
        ('inspection', 'Inspection'),
    ], string='Maintenance Type', required=True, default='preventive', tracking=True)

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Priority', default='medium', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    assigned_to = fields.Many2one('tapis.employee', string='Assigned To', tracking=True)

    scheduled_date = fields.Datetime(string='Scheduled Date', tracking=True)
    start_date = fields.Datetime(string='Start Date', tracking=True)
    end_date = fields.Datetime(string='End Date', tracking=True)

    downtime_hours = fields.Float(string='Downtime (Hours)', default=0.0)

    cost_estimated = fields.Float(string='Estimated Cost', default=0.0)
    cost_actual = fields.Float(string='Actual Cost', default=0.0)
    parts_cost = fields.Float(string='Parts Cost', default=0.0)
    labor_cost = fields.Float(string='Labor Cost', default=0.0)

    total_cost = fields.Float(
        string='Total Cost',
        compute='_compute_total_cost', store=True
    )

    description = fields.Text(string='Description')
    notes = fields.Text(string='Internal Notes')
    parts_notes = fields.Text(string='Parts Used')

    @api.depends('cost_actual', 'parts_cost', 'labor_cost')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost = rec.cost_actual + rec.parts_cost + rec.labor_cost

    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        for rec in self:
            if rec.equipment_id:
                rec.description = _('Maintenance for %s') % rec.equipment_id.name

    def action_schedule(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft orders can be scheduled.'))
            rec.state = 'scheduled'
            if not rec.scheduled_date:
                rec.scheduled_date = fields.Datetime.now()
            rec.message_post(body=_("Maintenance order scheduled."))
            template = self.env.ref('tapis_erp.email_template_maintenance_scheduled', False)
            if template:
                template.send_mail(rec.id, force_send=True)

    def action_start(self):
        for rec in self:
            if rec.state != 'scheduled':
                raise UserError(_('Only scheduled orders can be started.'))
            rec.state = 'in_progress'
            rec.start_date = fields.Datetime.now()
            rec.equipment_id.state = 'maintenance'
            rec.message_post(body=_("Maintenance started."))

    def action_done(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_('Only in-progress orders can be completed.'))
            rec.state = 'done'
            rec.end_date = fields.Datetime.now()
            if rec.start_date and rec.end_date:
                delta = rec.end_date - rec.start_date
                rec.downtime_hours = delta.total_seconds() / 3600.0
            rec.equipment_id.state = 'operational'
            rec.message_post(body=_("Maintenance completed."))

            rec.equipment_id._compute_condition()
            rec.equipment_id._compute_maintenance_dates()
            rec.equipment_id._compute_maintenance_totals()

    def action_cancel(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_('Completed orders cannot be cancelled.'))
            rec.state = 'cancelled'
            if rec.equipment_id.state == 'maintenance':
                has_other_active = self.search_count([
                    ('equipment_id', '=', rec.equipment_id.id),
                    ('state', 'in', ('scheduled', 'in_progress')),
                    ('id', '!=', rec.id),
                ])
                if not has_other_active:
                    rec.equipment_id.state = 'operational'
            rec.message_post(body=_("Maintenance order cancelled."))

    def action_validate(self):
        self.action_schedule()

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tapis.maintenance.order.code') or _('New')
        return super().create(vals)
