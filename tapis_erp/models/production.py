from odoo import _, models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta, datetime


class TapisProduction(models.Model):
    _name = 'tapis.production'
    _description = 'Tapis Production'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.audit.mixin']
    _order = 'planned_start_date, id'

    name = fields.Char(
        string="Production Reference",
        required=True,
        tracking=True
    )

    product_id = fields.Many2one(
        'tapis.product',
        string="Product",
        required=True,
        tracking=True
    )

    warehouse_id = fields.Many2one(
        'tapis.warehouse',
        string="Destination Warehouse",
        required=True,
        tracking=True
    )

    bom_id = fields.Many2one(
        'tapis.bom',
        string='Bill of Materials',
        tracking=True
    )

    design_id = fields.Many2one(
        'tapis.design',
        string="Design",
        tracking=True
    )

    quantity = fields.Integer(
        string="Quantity",
        default=1,
        tracking=True
    )

    material_cost = fields.Float(
        string='Material Cost',
        readonly=True
    )

    labor_cost = fields.Float(
        string='Labor Cost',
        default=0.0
    )

    overhead_cost = fields.Float(
        string='Overhead Cost',
        default=0.0
    )

    total_production_cost = fields.Float(
        string='Total Production Cost',
        compute='_compute_costs',
        store=True
    )

    unit_production_cost = fields.Float(
        string='Unit Production Cost',
        compute='_compute_costs',
        store=True
    )

    note = fields.Text(string="Notes")

    employee_ids = fields.Many2many('tapis.employee', string='Employees')

    equipment_id = fields.Many2one(
        'tapis.equipment', string='Equipment',
        tracking=True
    )

    quality_inspection_ids = fields.One2many(
        'tapis.quality.inspection',
        'production_id',
        string='Quality Inspections'
    )

    document_count = fields.Integer(compute='_compute_document_count')

    quality_inspection_count = fields.Integer(
        string='Quality Inspection Count',
        compute='_compute_quality_inspection_count'
    )

    latest_quality_result = fields.Selection([
        ('no_inspection', 'No Inspection'),
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], string='Latest Quality Result', compute='_compute_latest_quality_result', store=True)

    state = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='planned', tracking=True)

    planned_start_date = fields.Datetime(string='Planned Start Date', tracking=True)
    planned_end_date = fields.Datetime(string='Planned End Date', tracking=True)
    actual_start_date = fields.Datetime(string='Actual Start Date', readonly=True)
    actual_end_date = fields.Datetime(string='Actual End Date', readonly=True)

    estimated_hours = fields.Float(
        string='Estimated Hours', compute='_compute_estimation', store=True
    )
    estimated_days = fields.Float(
        string='Estimated Days', compute='_compute_estimation', store=True
    )

    resource_id = fields.Many2one(
        'tapis.production.resource', string='Assigned Resource', tracking=True
    )
    supervisor_id = fields.Many2one('res.users', string='Supervisor', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], default='1', string='Priority', tracking=True)

    delay_days = fields.Float(
        string='Delay (Days)', compute='_compute_performance', store=True
    )
    on_time_delivery = fields.Boolean(
        string='On Time', compute='_compute_performance', store=True
    )
    utilization_percent = fields.Float(
        string='Utilization %', compute='_compute_performance', store=True
    )

    predecessor_ids = fields.Many2many(
        'tapis.production',
        'production_predecessor_rel',
        'production_id', 'predecessor_id',
        string='Predecessors'
    )
    successor_ids = fields.Many2many(
        'tapis.production',
        'production_successor_rel',
        'production_id', 'successor_id',
        string='Successors'
    )

    @api.depends('material_cost', 'labor_cost', 'overhead_cost', 'quantity')
    def _compute_costs(self):
        for rec in self:
            rec.total_production_cost = rec.material_cost + rec.labor_cost + rec.overhead_cost
            rec.unit_production_cost = rec.total_production_cost / rec.quantity if rec.quantity else 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                bom = self.env['tapis.bom'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('active', '=', True),
                ], limit=1)
                rec.bom_id = bom.id if bom else False

    @api.depends('quality_inspection_ids')
    def _compute_quality_inspection_count(self):
        for rec in self:
            rec.quality_inspection_count = len(rec.quality_inspection_ids)

    @api.depends('quality_inspection_ids', 'quality_inspection_ids.result', 'quality_inspection_ids.state')
    def _compute_latest_quality_result(self):
        for rec in self:
            inspections = rec.quality_inspection_ids.filtered(lambda i: i.state == 'completed')
            if not inspections:
                rec.latest_quality_result = 'no_inspection'
            else:
                latest = inspections[:1]
                rec.latest_quality_result = latest.result

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('production_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('production_id', '=', self.id)],
            'context': {'default_production_id': self.id},
            'target': 'current',
        }

    def action_create_quality_inspection(self):
        self.ensure_one()
        inspection = self.env['tapis.quality.inspection'].create({
            'name': self.env['ir.sequence'].next_by_code('tapis.quality.inspection.code') or _('QI-New'),
            'production_id': self.id,
            'inspection_date': fields.Date.today(),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quality Inspection',
            'res_model': 'tapis.quality.inspection',
            'view_mode': 'form',
            'res_id': inspection.id,
            'target': 'current',
        }

    def action_view_quality_inspections(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Quality Inspections',
            'res_model': 'tapis.quality.inspection',
            'view_mode': 'tree,form',
            'domain': [('production_id', '=', self.id)],
            'target': 'current',
        }

    def _get_customer_email(self):
        sale = self.env['tapis.sale'].search([('product_id', '=', self.product_id.id)], limit=1)
        return sale._get_customer_email() if sale else self.env.company.email or 'yahyalaadam3@gmail.com'

    def _send_production_email(self, template_xmlid):
        template = self.env.ref(template_xmlid, False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _check_delayed(self):
        for rec in self:
            if rec.state == 'in_progress' and rec.planned_end_date:
                if fields.Datetime.now() > rec.planned_end_date:
                    template = self.env.ref('tapis_erp.email_template_production_delayed', False)
                    if template:
                        template.send_mail(rec.id, force_send=True)
                    rec.message_post(body=_("Production is delayed past planned end date."))

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'
            rec.message_post(
                body=_("Production started.")
            )
            rec._send_production_email('tapis_erp.email_template_production_started')

    def action_done(self):
        RawMaterial = self.env['tapis.raw.material']
        Quant = self.env['tapis.stock.quant']
        for rec in self:
            if not rec.bom_id:
                raise UserError(_(
                    'No Bill of Materials defined for product %s. '
                    'Please create a BOM before completing production.'
                ) % rec.product_id.name)

            for line in rec.bom_id.line_ids:
                required_qty = line.quantity * rec.quantity
                material = line.raw_material_id
                if material.stock_qty < required_qty:
                    raise UserError(_(
                        'Not enough stock of raw material %s. '
                        'Required: %s %s, Available: %s %s'
                    ) % (material.name, required_qty, material.uom, material.stock_qty, material.uom))
                material.stock_qty -= required_qty
                rec.message_post(
                    body=_("Consumed %s %s of %s for production.")
                          % (required_qty, material.uom, material.name)
                )

            rec.material_cost = rec.bom_id.total_material_cost * rec.quantity

            quant = Quant.search([
                ('product_id', '=', rec.product_id.id),
                ('warehouse_id', '=', rec.warehouse_id.id)
            ], limit=1)

            if quant:
                quant.quantity += rec.quantity
            else:
                Quant.create({
                    'product_id': rec.product_id.id,
                    'warehouse_id': rec.warehouse_id.id,
                    'quantity': rec.quantity,
                })

            self.env['tapis.stock.move'].create({
                'name': f'PROD-{rec.name}',
                'product_id': rec.product_id.id,
                'quantity': rec.quantity,
                'move_type': 'in',
                'destination_warehouse_id': rec.warehouse_id.id,
                'note': 'Production completed'
            })

            self.env['tapis.quality.inspection'].create({
                'name': self.env['ir.sequence'].next_by_code('tapis.quality.inspection.code') or _('QI-New'),
                'production_id': rec.id,
                'inspection_date': fields.Date.today(),
            })

            rec.state = 'done'

            rec.message_post(
                body=_("Production completed successfully. "
                       "Total cost: %s MAD, Unit cost: %s MAD")
                      % (rec.total_production_cost, rec.unit_production_cost)
            )

            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Production Finished'),
                note=_('Production order has been completed.')
            )

            rec._send_production_email('tapis_erp.email_template_production_completed')

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            rec.message_post(
                body=_("Production cancelled.")
            )

    @api.depends('quantity', 'product_id', 'design_id', 'design_id.total_weight_kg')
    def _compute_estimation(self):
        for rec in self:
            hours = rec.quantity * 0.5
            if rec.design_id and rec.design_id.total_weight_kg:
                hours = max(hours, rec.design_id.total_weight_kg * 0.2)
            rec.estimated_hours = hours
            cap = 8.0
            if rec.resource_id:
                cap = rec.resource_id.capacity_hours_per_day
            rec.estimated_days = hours / cap if cap else 1.0

    @api.depends('planned_end_date', 'actual_end_date', 'state',
                 'actual_start_date', 'planned_start_date')
    def _compute_performance(self):
        for rec in self:
            if rec.state == 'done' and rec.actual_end_date and rec.planned_end_date:
                delta = rec.actual_end_date - rec.planned_end_date
                rec.delay_days = delta.total_seconds() / 86400.0
                rec.on_time_delivery = rec.actual_end_date <= rec.planned_end_date
            else:
                rec.delay_days = 0.0
                rec.on_time_delivery = False
            if rec.state == 'in_progress' and rec.actual_start_date:
                elapsed = (fields.Datetime.now() - rec.actual_start_date).total_seconds() / 86400.0
                planned = rec.estimated_days
                rec.utilization_percent = min(100.0, (elapsed / planned * 100.0)) if planned else 0.0
            elif rec.state == 'done' and rec.actual_start_date and rec.actual_end_date:
                actual = (rec.actual_end_date - rec.actual_start_date).total_seconds() / 86400.0
                rec.utilization_percent = (rec.estimated_days / actual * 100.0) if actual else 0.0
            else:
                rec.utilization_percent = 0.0

    def action_auto_schedule(self):
        self.ensure_one()
        if not self.resource_id:
            raise UserError(_('Please assign a resource before scheduling.'))
        if not self.resource_id.active:
            raise UserError(_('The assigned resource is inactive.'))
        if not self.planned_start_date:
            self.planned_start_date = fields.Datetime.now()

        latest_predecessor_end = self.planned_start_date
        for pred in self.predecessor_ids:
            if pred.planned_end_date and pred.planned_end_date > latest_predecessor_end:
                latest_predecessor_end = pred.planned_end_date
        self.planned_start_date = latest_predecessor_end

        existing = self.search([
            ('resource_id', '=', self.resource_id.id),
            ('id', '!=', self.id),
            ('state', 'in', ('planned', 'in_progress')),
            ('planned_start_date', '!=', False),
        ], order='planned_start_date')

        slot_start = self.planned_start_date
        slot_end = slot_start + timedelta(hours=self.estimated_hours)
        max_lookahead_days = 180

        for _ in range(max_lookahead_days):
            conflict = False
            for other in existing:
                if other.planned_start_date and other.planned_end_date:
                    if slot_start < other.planned_end_date and slot_end > other.planned_start_date:
                        conflict = True
                        slot_start = other.planned_end_date
                        slot_end = slot_start + timedelta(hours=self.estimated_hours)
                        break
            if not conflict:
                break

        self.planned_start_date = slot_start
        self.planned_end_date = slot_end
        self.message_post(body=_("Auto-scheduled: %s → %s") % (
            slot_start.strftime('%Y-%m-%d %H:%M'),
            slot_end.strftime('%Y-%m-%d %H:%M'),
        ))

    def action_detect_conflicts(self):
        self.env['tapis.production.conflict'].search([
            ('production_id', 'in', self.ids)
        ]).unlink()
        for rec in self:
            if not rec.resource_id or not rec.planned_start_date:
                continue
            rec_end = rec.planned_start_date + timedelta(hours=rec.estimated_hours)
            others = self.search([
                ('resource_id', '=', rec.resource_id.id),
                ('id', '!=', rec.id),
                ('state', 'in', ('planned', 'in_progress')),
                ('planned_start_date', '!=', False),
            ])
            for other in others:
                other_end = other.planned_start_date + timedelta(
                    hours=other.estimated_hours
                )
                if rec.planned_start_date < other_end and rec_end > other.planned_start_date:
                    overlap_start = max(rec.planned_start_date, other.planned_start_date)
                    overlap_end = min(rec_end, other_end)
                    severity = 'critical' if rec.priority in ('2', '3') or other.priority in ('2', '3') else 'warning'
                    self.env['tapis.production.conflict'].create({
                        'production_id': rec.id,
                        'conflicting_production_id': other.id,
                        'resource_id': rec.resource_id.id,
                        'overlap_start': overlap_start,
                        'overlap_end': overlap_end,
                        'severity': severity,
                    })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Production Conflicts'),
            'res_model': 'tapis.production.conflict',
            'view_mode': 'tree,form',
            'domain': [('production_id', 'in', self.ids)],
            'target': 'current',
        }

    def action_start_production(self):
        for rec in self:
            if rec.state != 'planned':
                raise UserError(_('Only planned productions can be started.'))
            if not rec.resource_id:
                raise UserError(_('Assign a resource before starting production.'))
            rec.actual_start_date = fields.Datetime.now()
            rec.state = 'in_progress'
            rec.message_post(body=_("Production started on resource %s") % rec.resource_id.name)
            rec._send_production_email('tapis_erp.email_template_production_started')

    def action_finish_production(self):
        for rec in self:
            if rec.state != 'in_progress':
                raise UserError(_('Only in-progress productions can be finished.'))
            rec.actual_end_date = fields.Datetime.now()
            rec.state = 'done'
            rec.message_post(body=_("Production %s completed.") % rec.name)
            rec._send_production_email('tapis_erp.email_template_production_completed')
