from odoo import _, models, fields, api


class TapisProductionConflict(models.Model):
    _name = 'tapis.production.conflict'
    _description = 'Production Scheduling Conflict'
    _rec_name = 'production_id'

    production_id = fields.Many2one('tapis.production', required=True, string='Production')
    conflicting_production_id = fields.Many2one(
        'tapis.production', required=True, string='Conflicting With'
    )
    resource_id = fields.Many2one(
        'tapis.production.resource', required=True, string='Contested Resource'
    )
    overlap_start = fields.Datetime()
    overlap_end = fields.Datetime()
    severity = fields.Selection([
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ], default='warning')
