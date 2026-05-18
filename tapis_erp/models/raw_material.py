from odoo import models, fields, api


class TapisRawMaterial(models.Model):
    _name = 'tapis.raw.material'
    _description = 'Raw Material'
    _rec_name = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    uom = fields.Selection([
        ('kg', 'Kg'),
        ('meter', 'Meter'),
        ('liter', 'Liter'),
        ('piece', 'Piece'),
    ], string='Unit of Measure', default='kg')
    cost_per_unit = fields.Float(string='Cost per Unit', required=True)
    stock_qty = fields.Float(string='Stock Quantity', default=0.0)
    inventory_value = fields.Float(compute='_compute_inventory_value', store=True)
    supplier_id = fields.Many2one('tapis.supplier', string='Preferred Supplier')
    active = fields.Boolean(default=True)
    note = fields.Text()

    @api.depends('stock_qty', 'cost_per_unit')
    def _compute_inventory_value(self):
        for rec in self:
            rec.inventory_value = rec.stock_qty * rec.cost_per_unit

    def action_view_bom_lines(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'BOM Lines',
            'res_model': 'tapis.bom.line',
            'view_mode': 'tree,form',
            'domain': [('raw_material_id', '=', self.id)],
            'target': 'current',
        }
