from odoo import _, models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta
import math


class TapisProfitabilityAnalysis(models.Model):
    _name = 'tapis.profitability.analysis'
    _description = 'Profitability Analysis'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(required=True, readonly=True, default='New')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    analysis_type = fields.Selection([
        ('product', 'Product'),
        ('customer', 'Customer'),
        ('sale', 'Sale Order'),
        ('project', 'Project'),
        ('company', 'Company'),
    ], string='Analysis Type', required=True, default='product', tracking=True)

    product_id = fields.Many2one('tapis.product', string='Product', tracking=True)
    customer_id = fields.Many2one('tapis.customer', string='Customer', tracking=True)
    project_id = fields.Many2one('tapis.project', string='Project', tracking=True)

    date_from = fields.Date(string='From', tracking=True)
    date_to = fields.Date(string='To', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
    ], default='draft', tracking=True)

    revenue = fields.Float(string='Revenue', readonly=True)
    material_cost = fields.Float(string='Material Cost', readonly=True)
    labor_cost = fields.Float(string='Labor Cost', readonly=True)
    overhead_cost = fields.Float(string='Overhead Cost', readonly=True)
    total_cost = fields.Float(string='Total Cost', readonly=True)
    gross_profit = fields.Float(string='Gross Profit', readonly=True)
    net_profit = fields.Float(string='Net Profit', readonly=True)
    gross_margin_percent = fields.Float(string='Gross Margin %', readonly=True)
    net_margin_percent = fields.Float(string='Net Margin %', readonly=True)
    roi_percent = fields.Float(string='ROI %', readonly=True)

    line_ids = fields.One2many('tapis.profitability.analysis.line',
        'analysis_id', string='Analysis Lines')
    notes = fields.Text()

    def action_calculate(self):
        for rec in self:
            rec._compute_analysis()

    def action_approve(self):
        for rec in self:
            if rec.state != 'calculated':
                raise UserError(_('Only calculated analyses can be approved.'))
            rec.state = 'approved'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def _compute_analysis(self):
        self.ensure_one()
        domain = [('state', '=', 'delivered')]
        if self.date_from:
            domain.append(('order_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('order_date', '<=', self.date_to + timedelta(days=1)))

        Sale = self.env['tapis.sale']
        Prod = self.env['tapis.production']
        Project = self.env['tapis.project']

        if self.analysis_type == 'product' and self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
            sales = Sale.search(domain)
            productions = Prod.search([('product_id', '=', self.product_id.id),
                ('state', '=', 'done')])
        elif self.analysis_type == 'customer' and self.customer_id:
            domain.append(('customer_id', '=', self.customer_id.id))
            sales = Sale.search(domain)
            productions = Prod.search([])
        elif self.analysis_type == 'project' and self.project_id:
            project = self.project_id
            sales = Sale.search(domain)
            productions = Prod.search([])
        else:
            sales = Sale.search(domain)
            productions = Prod.search([('state', '=', 'done')])

        total_revenue = sum(sales.mapped('total_price'))
        total_mat_cost = sum(productions.mapped('material_cost'))
        total_labor_cost = sum(productions.mapped('labor_cost'))
        total_oh_cost = sum(productions.mapped('overhead_cost'))

        if self.analysis_type == 'product' and self.product_id:
            relevant_sales = sales.filtered(lambda s: s.product_id.id == self.product_id.id)
            total_revenue = sum(relevant_sales.mapped('total_price'))
        elif self.analysis_type == 'customer' and self.customer_id:
            relevant_sales = sales.filtered(lambda s: s.customer_id.id == self.customer_id.id)
            total_revenue = sum(relevant_sales.mapped('total_price'))
            product_ids = relevant_sales.mapped('product_id').ids
            productions = Prod.search([('product_id', 'in', product_ids), ('state', '=', 'done')])
            total_mat_cost = sum(productions.mapped('material_cost'))
            total_labor_cost = sum(productions.mapped('labor_cost'))
            total_oh_cost = sum(productions.mapped('overhead_cost'))
        elif self.analysis_type == 'project' and self.project_id:
            total_revenue = self.project_id.budget_amount or 0.0
            total_mat_cost = self.project_id.total_material_cost or 0.0
            total_labor_cost = self.project_id.total_labor_cost or 0.0
            total_oh_cost = self.project_id.total_overhead_cost or 0.0

        total_cost = total_mat_cost + total_labor_cost + total_oh_cost
        gross_profit = total_revenue - total_cost
        net_profit = gross_profit

        self.revenue = total_revenue
        self.material_cost = total_mat_cost
        self.labor_cost = total_labor_cost
        self.overhead_cost = total_oh_cost
        self.total_cost = total_cost
        self.gross_profit = gross_profit
        self.net_profit = net_profit
        self.gross_margin_percent = (gross_profit / total_revenue * 100.0) if total_revenue else 0.0
        self.net_margin_percent = (net_profit / total_revenue * 100.0) if total_revenue else 0.0
        self.roi_percent = (net_profit / total_cost * 100.0) if total_cost else 0.0
        self.state = 'calculated'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'tapis.profitability.analysis') or 'New'
        return super().create(vals_list)


class TapisProfitabilityAnalysisLine(models.Model):
    _name = 'tapis.profitability.analysis.line'
    _description = 'Profitability Analysis Line'
    _order = 'sequence'

    analysis_id = fields.Many2one('tapis.profitability.analysis',
        string='Analysis', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Item')
    revenue = fields.Float()
    material_cost = fields.Float()
    labor_cost = fields.Float()
    overhead_cost = fields.Float()
    total_cost = fields.Float()
    profit = fields.Float()
    margin_percent = fields.Float()
