from odoo import _, models, fields, api


class TapisApprovalRule(models.Model):
    _name = 'tapis.approval.rule'
    _description = 'Approval Rule'
    _order = 'category_id, sequence, id'

    category_id = fields.Many2one('tapis.approval.category', string='Category', required=True, ondelete='cascade')
    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    min_amount = fields.Float(string='Min Amount', default=0.0, help="Minimum amount to trigger this rule")
    max_amount = fields.Float(string='Max Amount', default=0.0, help="0 means no upper limit")
    cost_center_id = fields.Many2one('tapis.cost.center', string='Cost Center', help="Restrict rule to a specific cost center")
    approver_user_ids = fields.Many2many('res.users', string='Approvers', required=True)
    required_approvals = fields.Integer(string='Required Approvals', default=1, help="Number of approvals required at this level")
    is_sequential = fields.Boolean(string='Sequential', default=False, help="Approvals must happen in sequence order")
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('min_amount', 'max_amount')
    def _check_amounts(self):
        for rec in self:
            if rec.max_amount > 0 and rec.min_amount > rec.max_amount:
                raise models.ValidationError(_('Min amount cannot exceed max amount.'))

    @api.constrains('required_approvals')
    def _check_required_approvals(self):
        for rec in self:
            if rec.required_approvals < 1:
                raise models.ValidationError(_('Required approvals must be at least 1.'))
            if rec.required_approvals > len(rec.approver_user_ids):
                raise models.ValidationError(_('Required approvals cannot exceed the number of approvers.'))
