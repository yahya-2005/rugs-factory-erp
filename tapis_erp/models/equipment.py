from odoo import _, models, fields, api


class TapisEquipment(models.Model):
    _name = 'tapis.equipment'
    _description = 'Equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Equipment', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, readonly=True, default=lambda s: _('New'))

    category = fields.Selection([
        ('loom', 'Loom'),
        ('dyeing', 'Dyeing Machine'),
        ('washing', 'Washing Machine'),
        ('drying', 'Drying Machine'),
        ('cutting', 'Cutting Machine'),
        ('finishing', 'Finishing Machine'),
        ('other', 'Other'),
    ], string='Category', required=True, tracking=True)

    tag_ids = fields.Many2many('tapis.tag', string='Tags')

    location = fields.Char(string='Location', tracking=True)
    notes = fields.Text(string='Notes')

    state = fields.Selection([
        ('operational', 'Operational'),
        ('broken', 'Broken'),
        ('maintenance', 'Under Maintenance'),
        ('retired', 'Retired'),
    ], string='Status', default='operational', required=True, tracking=True)

    condition_percent = fields.Integer(
        string='Condition (%)', compute='_compute_condition', store=True, default=100
    )

    last_maintenance_date = fields.Date(
        string='Last Maintenance',
        compute='_compute_maintenance_dates', store=True
    )
    next_maintenance_date = fields.Date(
        string='Next Maintenance',
        compute='_compute_maintenance_dates', store=True
    )
    overdue_maintenance = fields.Boolean(
        string='Overdue Maintenance',
        compute='_compute_maintenance_dates', store=True
    )

    total_maintenance_cost = fields.Float(
        string='Total Maintenance Cost',
        compute='_compute_maintenance_totals', store=True
    )
    total_downtime_hours = fields.Float(
        string='Total Downtime (Hours)',
        compute='_compute_maintenance_totals', store=True
    )

    maintenance_count = fields.Integer(
        string='Maintenance Orders',
        compute='_compute_maintenance_counts', store=True
    )
    maintenance_open_count = fields.Integer(
        string='Open Maintenance Orders',
        compute='_compute_maintenance_counts', store=True
    )

    maintenance_order_ids = fields.One2many(
        'tapis.maintenance.order', 'equipment_id',
        string='Maintenance Orders'
    )

    image = fields.Binary(string='Image', attachment=True)
    document_count = fields.Integer(compute='_compute_document_count')

    @api.depends('maintenance_order_ids', 'maintenance_order_ids.state',
                 'maintenance_order_ids.end_date')
    def _compute_maintenance_dates(self):
        for rec in self:
            done_orders = rec.maintenance_order_ids.filtered(
                lambda o: o.state == 'done' and o.end_date
            )
            rec.last_maintenance_date = done_orders.sorted(
                key=lambda o: o.end_date, reverse=True
            )[:1].end_date if done_orders else False

            scheduled_orders = rec.maintenance_order_ids.filtered(
                lambda o: o.state in ('scheduled', 'in_progress') and o.scheduled_date
            )
            rec.next_maintenance_date = scheduled_orders.sorted(
                key=lambda o: o.scheduled_date
            )[:1].scheduled_date if scheduled_orders else False

            rec.overdue_maintenance = bool(
                scheduled_orders.filtered(
                    lambda o: o.state == 'scheduled' and o.scheduled_date < fields.Date.today()
                )
            )

    @api.depends('maintenance_order_ids', 'maintenance_order_ids.state',
                 'maintenance_order_ids.cost_actual')
    def _compute_maintenance_totals(self):
        for rec in self:
            done_orders = rec.maintenance_order_ids.filtered(lambda o: o.state == 'done')
            rec.total_maintenance_cost = sum(done_orders.mapped('cost_actual'))
            rec.total_downtime_hours = sum(done_orders.mapped('downtime_hours'))

    @api.depends('maintenance_order_ids', 'maintenance_order_ids.state')
    def _compute_maintenance_counts(self):
        for rec in self:
            rec.maintenance_count = len(rec.maintenance_order_ids)
            rec.maintenance_open_count = len(
                rec.maintenance_order_ids.filtered(
                    lambda o: o.state in ('draft', 'scheduled', 'in_progress')
                )
            )

    @api.depends('state', 'total_maintenance_cost')
    def _compute_condition(self):
        for rec in self:
            if rec.state == 'retired':
                rec.condition_percent = 0
            elif rec.state == 'broken':
                rec.condition_percent = max(0, 30 - rec.total_maintenance_cost / 1000)
            elif rec.state == 'maintenance':
                rec.condition_percent = max(0, 50 - rec.total_maintenance_cost / 1000)
            elif rec.state == 'operational':
                rec.condition_percent = min(100, max(70, 100 - rec.total_maintenance_cost / 500))
            else:
                rec.condition_percent = 100

    def action_set_running(self):
        for rec in self:
            rec.state = 'operational'
            rec.message_post(body=_("Equipment set to operational."))

    def action_set_broken(self):
        for rec in self:
            rec.state = 'broken'
            rec.message_post(body=_("Equipment marked as broken."))

    def action_set_maintenance(self):
        for rec in self:
            rec.state = 'maintenance'
            rec.message_post(body=_("Equipment sent to maintenance."))

    def action_set_retired(self):
        for rec in self:
            rec.state = 'retired'
            rec.message_post(body=_("Equipment retired."))

    def action_view_maintenance_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Maintenance Orders',
            'res_model': 'tapis.maintenance.order',
            'view_mode': 'tree,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {'default_equipment_id': self.id},
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tapis.equipment.code') or _('New')
        return super().create(vals)

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('equipment_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('equipment_id', '=', self.id)],
            'context': {'default_equipment_id': self.id},
            'target': 'current',
        }
