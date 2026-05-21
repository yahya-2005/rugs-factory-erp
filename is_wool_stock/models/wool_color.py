from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WoolColor(models.Model):
    _name = 'wool.color'
    _description = 'Wool Color Reference'
    _order = 'code'
    _rec_name = 'display_name_full'

    name = fields.Char(required=True)
    code = fields.Char(required=True, unique=True)
    display_name_full = fields.Char(compute='_compute_display_name_full', store=True)
    description = fields.Text()
    color_hex = fields.Char(help='Hex color code e.g. #D9C6A5')
    tag_color = fields.Integer(default=0)
    active = fields.Boolean(default=True)

    qty_on_hand = fields.Float(compute='_compute_stock_quantities', store=True, string='On Hand')
    qty_reserved = fields.Float(compute='_compute_stock_quantities', store=True, string='Reserved')
    qty_available = fields.Float(compute='_compute_stock_quantities', store=True, string='Available')
    reorder_point = fields.Float(string='Reorder Point', default=10.0)
    minimum_stock = fields.Float(string='Minimum Stock', default=0.0)
    maximum_stock = fields.Float(string='Maximum Stock', default=500.0)
    unit_cost = fields.Float(string='Unit Cost')
    inventory_value = fields.Float(compute='_compute_stock_quantities', store=True, string='Inventory Value')

    supplier_id = fields.Many2one('res.partner', string='Preferred Supplier')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    move_ids = fields.One2many('wool.stock.move', 'wool_color_id', string='Stock Moves')
    move_count = fields.Integer(compute='_compute_move_count')

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Color code must be unique!'),
    ]

    @api.depends('name', 'code')
    def _compute_display_name_full(self):
        for rec in self:
            parts = [rec.code] if rec.code else []
            if rec.name:
                parts.append(rec.name)
            rec.display_name_full = ' - '.join(parts) if parts else rec.code or rec.name or ''

    @api.depends('move_ids.state', 'move_ids.move_type', 'move_ids.quantity')
    def _compute_stock_quantities(self):
        Move = self.env['wool.stock.move']
        for rec in self:
            moves = Move.search([('wool_color_id', '=', rec.id), ('state', '=', 'done')])
            qty_in = sum(m.quantity for m in moves if m.move_type == 'in')
            qty_out = sum(m.quantity for m in moves if m.move_type == 'out')
            qty_adj = sum(m.quantity for m in moves if m.move_type == 'adjustment')
            qty_reserved = sum(m.quantity for m in moves if m.move_type == 'reservation')
            qty_release = sum(m.quantity for m in moves if m.move_type == 'release')

            on_hand = qty_in - qty_out + qty_adj - qty_reserved + qty_release
            reserved = qty_reserved - qty_release
            rec.qty_on_hand = on_hand
            rec.qty_reserved = max(reserved, 0.0)
            rec.qty_available = on_hand - max(reserved, 0.0)
            rec.inventory_value = on_hand * rec.unit_cost

    def _compute_move_count(self):
        for rec in self:
            rec.move_count = self.env['wool.stock.move'].search_count([('wool_color_id', '=', rec.id)])

    def action_open_moves(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Stock Moves - %s') % self.display_name_full,
            'res_model': 'wool.stock.move',
            'view_mode': 'tree,form',
            'domain': [('wool_color_id', '=', self.id)],
            'context': {'default_wool_color_id': self.id},
            'target': 'current',
        }

    def action_adjust_stock(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Adjust Stock - %s') % self.display_name_full,
            'res_model': 'wool.stock.adjustment',
            'view_mode': 'form',
            'context': {
                'default_wool_color_id': self.id,
                'default_current_qty': self.qty_on_hand,
            },
            'target': 'new',
        }

    @api.model
    def cron_check_reorder(self):
        colors = self.search([('active', '=', True), ('qty_on_hand', '<=', 'reorder_point')])
        for color in colors:
            if color.supplier_id:
                template = self.env.ref('is_wool_stock.email_template_low_stock', False)
                if template:
                    template.send_mail(color.id, force_send=True)
        return True
