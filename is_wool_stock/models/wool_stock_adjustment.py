from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WoolStockAdjustment(models.Model):
    _name = 'wool.stock.adjustment'
    _description = 'Wool Stock Adjustment'
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True)
    date = fields.Datetime(default=fields.Datetime.now, required=True)
    wool_color_id = fields.Many2one('wool.color', string='Wool Color', required=True)
    current_qty = fields.Float(string='Current Quantity', readonly=True)
    counted_qty = fields.Float(string='Counted Quantity', required=True)
    difference_qty = fields.Float(compute='_compute_difference', store=True, string='Difference')
    reason = fields.Selection([
        ('count_error', 'Counting Error'),
        ('damage', 'Damage / Waste'),
        ('theft', 'Theft / Loss'),
        ('return', 'Return to Supplier'),
        ('other', 'Other'),
    ], string='Reason', default='count_error')
    notes = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('current_qty', 'counted_qty')
    def _compute_difference(self):
        for rec in self:
            rec.difference_qty = rec.counted_qty - rec.current_qty

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('wool.stock.adjustment') or _('New')
            if not vals.get('current_qty') and vals.get('wool_color_id'):
                color = self.env['wool.color'].browse(vals['wool_color_id'])
                vals['current_qty'] = color.qty_on_hand
        return super().create(vals_list)

    def action_validate(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft adjustments can be validated.'))
            diff = rec.difference_qty
            if abs(diff) < 0.001:
                raise UserError(_('No difference to adjust. Counted quantity equals current quantity.'))
            self.env['wool.stock.move'].create({
                'wool_color_id': rec.wool_color_id.id,
                'move_type': 'adjustment',
                'quantity': diff,
                'unit_cost': rec.wool_color_id.unit_cost,
                'reference': rec.name,
                'notes': rec.notes or rec.reason,
                'state': 'done',
            })
            rec.state = 'validated'

    def action_cancel(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft adjustments can be cancelled.'))
            rec.state = 'cancelled'
