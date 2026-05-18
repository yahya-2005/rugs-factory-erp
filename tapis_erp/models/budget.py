from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisBudget(models.Model):
    _name = 'tapis.budget'
    _description = 'Budget'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.approval.mixin', 'tapis.communication.mixin', 'tapis.audit.mixin', 'tapis.signature.mixin']
    _rec_name = 'name'
    _order = 'fiscal_year desc, id desc'

    name = fields.Char(string='Budget Reference', required=True, readonly=True, default=lambda s: _('New'), tracking=True)
    cost_center_id = fields.Many2one('tapis.cost.center', string='Cost Center', required=True, tracking=True)
    fiscal_year = fields.Char(string='Fiscal Year', required=True, default=lambda s: str(fields.Date.today().year), tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', required=True, tracking=True)
    line_ids = fields.One2many('tapis.budget.line', 'budget_id', string='Budget Lines')
    total_planned = fields.Float(string='Total Planned (MAD)', compute='_compute_totals', store=True)
    total_actual = fields.Float(string='Total Actual (MAD)', compute='_compute_totals', store=True)
    total_variance = fields.Float(string='Total Variance (MAD)', compute='_compute_totals', store=True)
    notes = fields.Text(string='Notes')
    document_count = fields.Integer(compute='_compute_document_count')
    approval_count = fields.Integer(compute='_compute_approval_count')

    @api.depends('line_ids', 'line_ids.planned_amount', 'line_ids.actual_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_planned = sum(rec.line_ids.mapped('planned_amount'))
            rec.total_actual = sum(rec.line_ids.mapped('actual_amount'))
            rec.total_variance = rec.total_planned - rec.total_actual

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft budgets can be confirmed.'))
            rec.state = 'confirmed'
            rec.message_post(body=_('Budget confirmed.'))

    def action_approve(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_('Only confirmed budgets can be approved.'))
            rec.state = 'approved'
            rec.message_post(body=_('Budget approved.'))

    def action_close(self):
        for rec in self:
            if rec.state not in ('approved', 'confirmed'):
                raise UserError(_('Only approved or confirmed budgets can be closed.'))
            rec.state = 'closed'
            rec.message_post(body=_('Budget closed.'))

    def action_draft(self):
        for rec in self:
            if rec.state not in ('confirmed', 'approved'):
                raise UserError(_('Only confirmed or approved budgets can be reset to draft.'))
            rec.state = 'draft'
            rec.message_post(body=_('Budget reset to draft.'))

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tapis.budget.code') or _('New')
        return super().create(vals)

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('budget_id', '=', rec.id)])

    def _compute_approval_count(self):
        for rec in self:
            rec.approval_count = self.env['tapis.approval.request'].search_count([
                ('reference_model', '=', 'tapis.budget'), ('reference_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('budget_id', '=', self.id)],
            'context': {'default_budget_id': self.id},
            'target': 'current',
        }

    def _get_approval_amount(self):
        return self.total_planned

    def _get_approval_category_code(self):
        return 'budget'

    def _on_approval_approved(self):
        self.state = 'approved'
        self.message_post(body=_('Budget auto-approved by approval workflow.'))

    def _on_approval_rejected(self):
        self.state = 'draft'
        self.message_post(body=_('Budget returned to draft due to rejection.'))


class TapisBudgetLine(models.Model):
    _name = 'tapis.budget.line'
    _description = 'Budget Line'
    _order = 'budget_id, id'

    budget_id = fields.Many2one('tapis.budget', string='Budget', required=True, ondelete='cascade')
    category = fields.Selection([
        ('materials', 'Raw Materials'),
        ('labor', 'Labor'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment & Maintenance'),
        ('transport', 'Transport & Logistics'),
        ('marketing', 'Marketing & Sales'),
        ('administrative', 'Administrative'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other')
    planned_amount = fields.Float(string='Planned Amount (MAD)', required=True, default=0.0)
    actual_amount = fields.Float(string='Actual Amount (MAD)', default=0.0)
    variance = fields.Float(string='Variance (MAD)', compute='_compute_variance', store=True)
    notes = fields.Text(string='Notes')

    @api.depends('planned_amount', 'actual_amount')
    def _compute_variance(self):
        for rec in self:
            rec.variance = rec.planned_amount - rec.actual_amount

    _sql_constraints = [
        ('budget_category_unique', 'UNIQUE(budget_id, category)',
         'Each category can only appear once per budget.'),
    ]
