from odoo import _, models, fields, api


class TapisCostAllocationRule(models.Model):
    _name = 'tapis.cost.allocation.rule'
    _description = 'Cost Allocation Rule'
    _order = 'cost_center_id, sequence'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    cost_center_id = fields.Many2one('tapis.cost.center', string='Cost Center',
        required=True, ondelete='cascade')
    allocation_method = fields.Selection([
        ('fixed_percentage', 'Fixed Percentage'),
        ('direct_labor_hours', 'Direct Labor Hours'),
        ('machine_hours', 'Machine Hours'),
        ('production_qty', 'Production Quantity'),
        ('revenue', 'Revenue'),
    ], string='Allocation Method', required=True, default='fixed_percentage')
    percentage = fields.Float(string='Percentage (%)', default=0.0,
        help='Used when method is Fixed Percentage')
    active = fields.Boolean(default=True)
