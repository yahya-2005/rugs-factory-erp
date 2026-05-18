from odoo import models, fields, api


class DesignColorLine(models.Model):
    _name = 'tapis.design.color.line'
    _description = 'Design Color Composition Line'
    _order = 'sequence, id'

    design_id = fields.Many2one('tapis.design', string='Design', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)

    color_code = fields.Char(string='Color Code', required=True)
    color_name = fields.Char(string='Color Name')
    hex_color = fields.Char(string='Hex Color')
    color_preview = fields.Integer(string='Color Preview')

    percentage = fields.Float(string='Percentage (%)', required=True)

    weight_kg = fields.Float(string='Weight (kg)', compute='_compute_weight_kg', store=True)

    wool_product_id = fields.Many2one('tapis.product', string='Wool Product')

    estimated_cost = fields.Float(string='Estimated Cost', compute='_compute_estimated_cost', store=True)

    note = fields.Text(string='Note')

    _sql_constraints = [
        ('check_percentage_min', 'CHECK(percentage >= 0)', 'Percentage must be 0 or greater.'),
        ('check_percentage_max', 'CHECK(percentage <= 100)', 'Percentage cannot exceed 100.'),
    ]

    @api.depends('design_id.total_weight_kg', 'percentage')
    def _compute_weight_kg(self):
        for rec in self:
            if rec.design_id and rec.design_id.total_weight_kg and rec.percentage:
                rec.weight_kg = rec.design_id.total_weight_kg * (rec.percentage / 100.0)
            else:
                rec.weight_kg = 0.0

    @api.depends('weight_kg', 'wool_product_id', 'wool_product_id.cost')
    def _compute_estimated_cost(self):
        for rec in self:
            if rec.wool_product_id and rec.wool_product_id.cost:
                rec.estimated_cost = rec.weight_kg * rec.wool_product_id.cost
            else:
                rec.estimated_cost = 0.0
