from odoo import models, fields, api


class TapisCrmStage(models.Model):
    _name = 'tapis.crm.stage'
    _description = 'CRM Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    probability = fields.Float(string='Probability (%)', default=0.0)
    fold = fields.Boolean(string='Folded in Pipeline', default=False)
    color = fields.Integer(string='Color', default=0)
    is_won = fields.Boolean(string='Won Stage', default=False)
    is_lost = fields.Boolean(string='Lost Stage', default=False)
    active = fields.Boolean(string='Active', default=True)

    def init(self):
        if not self.search([], limit=1):
            stages = [
                {'name': 'New Lead', 'sequence': 10, 'probability': 10},
                {'name': 'Qualified', 'sequence': 20, 'probability': 30},
                {'name': 'Proposal', 'sequence': 30, 'probability': 50},
                {'name': 'Negotiation', 'sequence': 40, 'probability': 75},
                {'name': 'Won', 'sequence': 50, 'probability': 100, 'is_won': True},
                {'name': 'Lost', 'sequence': 60, 'probability': 0, 'is_lost': True},
            ]
            for vals in stages:
                self.create(vals)
