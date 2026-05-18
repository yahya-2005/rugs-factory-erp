from odoo import models, fields, api, _
from odoo.exceptions import UserError


class IntercompanyRule(models.Model):
    _name = 'tapis.intercompany.rule'
    _description = 'Intercompany Rule'
    _rec_name = 'source_company_id'
    _sql_constraints = [
        ('rule_unique', 'UNIQUE(source_company_id, target_company_id)',
         'A rule between these companies already exists.'),
    ]

    source_company_id = fields.Many2one('res.company', string='Source Company', required=True)
    target_company_id = fields.Many2one('res.company', string='Target Company', required=True)
    auto_create_purchase = fields.Boolean(string='Auto-Create Purchase', default=True)
    auto_create_sale = fields.Boolean(string='Auto-Create Sale', default=True)
    auto_validate_documents = fields.Boolean(string='Auto-Validate Documents', default=False)
    active = fields.Boolean(default=True)
    margin_percent = fields.Float(string='Intercompany Margin (%)', default=0.0,
        help='Markup percentage applied to intercompany transfers.')

    def _get_rule(self, source_company, target_company):
        return self.search([
            ('source_company_id', '=', source_company.id if hasattr(source_company, 'id') else source_company),
            ('target_company_id', '=', target_company.id if hasattr(target_company, 'id') else target_company),
            ('active', '=', True),
        ], limit=1)
