from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisProduction(models.Model):
    _name = 'tapis.production'
    _description = 'Tapis Production'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.audit.mixin']

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

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'
            rec.message_post(
                body=_("Production started.")
            )

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

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            rec.message_post(
                body=_("Production cancelled.")
            )
