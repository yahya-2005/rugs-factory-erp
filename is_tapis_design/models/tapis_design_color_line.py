from odoo import _, api, fields, models


class WoolDesignColorLine(models.Model):
    _name = 'wool.design.color.line'
    _description = 'Design Color Composition Line'
    _order = 'sequence, id'

    design_id = fields.Many2one('wool.design', string='Design', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)

    wool_color_id = fields.Many2one('wool.color', string='Wool Color', required=True)

    color_code = fields.Char(related='wool_color_id.code', store=True, readonly=True)
    color_name = fields.Char(related='wool_color_id.name', store=True, readonly=True)
    color_hex = fields.Char(related='wool_color_id.color_hex', readonly=True)
    tag_color = fields.Integer(related='wool_color_id.tag_color', readonly=True)
    qty_available = fields.Float(related='wool_color_id.qty_available', readonly=True)

    percentage = fields.Float(required=True)
    estimated_weight_kg = fields.Float(compute='_compute_weight_kg', store=True)

    note = fields.Text()

    _sql_constraints = [
        ('check_percentage_min', 'CHECK(percentage >= 0)', 'Percentage must be 0 or greater.'),
        ('check_percentage_max', 'CHECK(percentage <= 100)', 'Percentage cannot exceed 100.'),
    ]

    @api.depends('design_id.estimated_weight_kg', 'percentage')
    def _compute_weight_kg(self):
        for rec in self:
            if rec.design_id and rec.design_id.estimated_weight_kg and rec.percentage:
                rec.estimated_weight_kg = rec.design_id.estimated_weight_kg * (rec.percentage / 100.0)
            else:
                rec.estimated_weight_kg = 0.0
