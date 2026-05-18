from odoo import _, models, fields, api


class TapisCostCenter(models.Model):
    _name = 'tapis.cost.center'
    _description = 'Cost Center'
    _rec_name = 'name'
    _order = 'code'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True, readonly=True, default=lambda s: _('New'))
    manager_id = fields.Many2one('tapis.employee', string='Manager')
    parent_id = fields.Many2one('tapis.cost.center', string='Parent Cost Center')
    child_ids = fields.One2many('tapis.cost.center', 'parent_id', string='Child Cost Centers')
    cost_type = fields.Selection([
        ('department', 'Department'),
        ('production', 'Production'),
        ('project', 'Project'),
        ('overhead', 'Overhead'),
        ('administrative', 'Administrative'),
    ], string='Type', default='department', required=True)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    budget_ids = fields.One2many('tapis.budget', 'cost_center_id', string='Budgets')
    budget_count = fields.Integer(string='Budget Count', compute='_compute_budget_counts', store=True)
    total_planned_budget = fields.Float(string='Total Planned Budget (MAD)', compute='_compute_budget_totals', store=True)
    total_actual_cost = fields.Float(string='Total Actual Cost (MAD)', compute='_compute_budget_totals', store=True)

    allocation_rule_ids = fields.One2many('tapis.cost.allocation.rule',
        'cost_center_id', string='Allocation Rules')
    allocation_rule_count = fields.Integer(compute='_compute_allocation_rule_count',
        string='Allocation Rule Count')

    @api.depends('budget_ids')
    def _compute_budget_counts(self):
        for rec in self:
            rec.budget_count = len(rec.budget_ids)

    @api.depends('budget_ids', 'budget_ids.state', 'budget_ids.total_planned', 'budget_ids.total_actual')
    def _compute_budget_totals(self):
        for rec in self:
            budgets = rec.budget_ids.filtered(lambda b: b.state in ('confirmed', 'approved', 'closed'))
            rec.total_planned_budget = sum(budgets.mapped('total_planned'))
            rec.total_actual_cost = sum(budgets.mapped('total_actual'))

    @api.depends('allocation_rule_ids')
    def _compute_allocation_rule_count(self):
        for rec in self:
            rec.allocation_rule_count = len(rec.allocation_rule_ids)

    def action_view_budgets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Budgets',
            'res_model': 'tapis.budget',
            'view_mode': 'tree,form',
            'domain': [('cost_center_id', '=', self.id)],
            'context': {'default_cost_center_id': self.id},
        }

    def action_view_allocation_rules(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Allocation Rules',
            'res_model': 'tapis.cost.allocation.rule',
            'view_mode': 'tree,form',
            'domain': [('cost_center_id', '=', self.id)],
            'context': {'default_cost_center_id': self.id},
        }

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tapis.cost.center.code') or _('New')
        return super().create(vals)
