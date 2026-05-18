from odoo import _, models, fields, api


class TapisApprovalCategory(models.Model):
    _name = 'tapis.approval.category'
    _description = 'Approval Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    code = fields.Char(string='Category Code', required=True, help="Used to match from integrated models (e.g. 'purchase', 'budget', 'document')")
    model_name = fields.Char(string='Target Model', required=True, help="Technical model name (e.g. tapis.purchase)")
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    auto_apply = fields.Boolean(string='Auto-Apply', default=True, help="Automatically submit for approval when conditions match")
    description = fields.Text(string='Description')
    rule_ids = fields.One2many('tapis.approval.rule', 'category_id', string='Approval Rules')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Category code must be unique.'),
    ]
