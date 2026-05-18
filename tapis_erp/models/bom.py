from odoo import _, models, fields, api


class TapisBom(models.Model):
    _name = 'tapis.bom'
    _description = 'Bill of Materials'
    _rec_name = 'name'

    name = fields.Char(required=True)
    product_id = fields.Many2one('tapis.product', string='Product', required=True)
    version = fields.Char(default='1.0')
    line_ids = fields.One2many('tapis.bom.line', 'bom_id', string='BOM Lines')
    total_material_cost = fields.Float(compute='_compute_costs', store=True)
    active = fields.Boolean(default=True)
    note = fields.Text()

    @api.depends('line_ids', 'line_ids.line_cost')
    def _compute_costs(self):
        for rec in self:
            rec.total_material_cost = sum(rec.line_ids.mapped('line_cost'))

    def action_open_product(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Product',
            'res_model': 'tapis.product',
            'view_mode': 'form',
            'res_id': self.product_id.id,
            'target': 'current',
        }


class TapisBomLine(models.Model):
    _name = 'tapis.bom.line'
    _description = 'BOM Line'

    bom_id = fields.Many2one('tapis.bom', string='BOM', required=True, ondelete='cascade')
    raw_material_id = fields.Many2one('tapis.raw.material', string='Raw Material', required=True)
    quantity = fields.Float(required=True)
    unit_cost = fields.Float(related='raw_material_id.cost_per_unit', store=True, string='Unit Cost')
    line_cost = fields.Float(compute='_compute_line_cost', store=True)

    @api.depends('quantity', 'unit_cost')
    def _compute_line_cost(self):
        for rec in self:
            rec.line_cost = rec.quantity * rec.unit_cost
