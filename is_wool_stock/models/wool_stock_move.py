from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WoolStockMove(models.Model):
    _name = 'wool.stock.move'
    _description = 'Wool Stock Movement'
    _order = 'date desc, id desc'

    name = fields.Char(default=lambda self: _('New'), readonly=True)
    date = fields.Datetime(default=fields.Datetime.now, required=True)
    wool_color_id = fields.Many2one('wool.color', string='Wool Color', required=True)
    move_type = fields.Selection([
        ('in', 'Incoming'),
        ('out', 'Outgoing'),
        ('adjustment', 'Adjustment'),
        ('reservation', 'Reservation'),
        ('release', 'Release'),
    ], string='Type', required=True, default='in')
    quantity = fields.Float(required=True)
    unit_cost = fields.Float(string='Unit Cost')
    total_value = fields.Float(compute='_compute_total_value', store=True)
    reference = fields.Char()
    source_document = fields.Char(string='Source Document')
    notes = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('quantity', 'unit_cost')
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = rec.quantity * rec.unit_cost

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('wool.stock.move') or _('New')
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft moves can be confirmed.'))
            if rec.quantity <= 0:
                raise UserError(_('Quantity must be positive.'))
            if rec.move_type == 'out':
                color = rec.wool_color_id
                if color.qty_available < rec.quantity:
                    raise UserError(_(
                        'Insufficient available stock for %s. Available: %.2f, Requested: %.2f') % (
                        color.display_name_full, color.qty_available, rec.quantity))
            if not rec.unit_cost and rec.move_type == 'in':
                rec.unit_cost = rec.wool_color_id.unit_cost
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft moves can be cancelled.'))
            rec.state = 'cancelled'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
