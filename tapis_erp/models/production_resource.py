from odoo import _, models, fields, api


class TapisProductionResource(models.Model):
    _name = 'tapis.production.resource'
    _description = 'Production Resource'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    resource_type = fields.Selection([
        ('loom', 'Loom'),
        ('weaving_team', 'Weaving Team'),
        ('dyeing_station', 'Dyeing Station'),
        ('finishing_station', 'Finishing Station'),
    ], required=True)
    capacity_hours_per_day = fields.Float(default=8.0)
    efficiency_percent = fields.Float(default=100.0)
    active = fields.Boolean(default=True)
    supervisor_id = fields.Many2one('res.users')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    production_ids = fields.One2many('tapis.production', 'resource_id', string='Assignments')
    conflict_count = fields.Integer(compute='_compute_conflict_count')
    total_assigned_hours = fields.Float(compute='_compute_assigned_hours')

    @api.depends('production_ids', 'production_ids.state')
    def _compute_conflict_count(self):
        for rec in self:
            rec.conflict_count = self.env['tapis.production.conflict'].search_count(
                [('resource_id', '=', rec.id)]
            )

    @api.depends('production_ids', 'production_ids.estimated_hours', 'production_ids.state')
    def _compute_assigned_hours(self):
        for rec in self:
            active = rec.production_ids.filtered(
                lambda p: p.state in ('planned', 'in_progress')
            )
            rec.total_assigned_hours = sum(active.mapped('estimated_hours'))
