from odoo import _, models, fields, api


class TapisProductCostExt(models.Model):
    _inherit = 'tapis.product'

    standard_material_cost = fields.Float(string='Std Material Cost', default=0.0)
    standard_labor_cost = fields.Float(string='Std Labor Cost', default=0.0)
    standard_overhead_cost = fields.Float(string='Std Overhead Cost', default=0.0)
    total_standard_cost = fields.Float(compute='_compute_standard_cost', store=True,
        string='Total Std Cost')
    gross_margin_percent = fields.Float(compute='_compute_gross_margin', store=True,
        string='Gross Margin %')

    @api.depends('standard_material_cost', 'standard_labor_cost', 'standard_overhead_cost')
    def _compute_standard_cost(self):
        for rec in self:
            rec.total_standard_cost = (rec.standard_material_cost + rec.standard_labor_cost +
                rec.standard_overhead_cost)

    @api.depends('price', 'total_standard_cost')
    def _compute_gross_margin(self):
        for rec in self:
            if rec.price and rec.price > 0:
                rec.gross_margin_percent = ((rec.price - rec.total_standard_cost) /
                    rec.price * 100.0)
            else:
                rec.gross_margin_percent = 0.0


class TapisProductionCostExt(models.Model):
    _inherit = 'tapis.production'

    standard_material_cost = fields.Float(string='Std Material Cost', default=0.0)
    standard_labor_cost = fields.Float(string='Std Labor Cost', default=0.0)
    standard_overhead_cost = fields.Float(string='Std Overhead Cost', default=0.0)
    total_standard_cost = fields.Float(compute='_compute_std_total', store=True,
        string='Total Std Cost')

    material_variance = fields.Float(compute='_compute_variances', store=True,
        string='Material Variance')
    labor_variance = fields.Float(compute='_compute_variances', store=True,
        string='Labor Variance')
    overhead_variance = fields.Float(compute='_compute_variances', store=True,
        string='Overhead Variance')
    total_variance = fields.Float(compute='_compute_variances', store=True,
        string='Total Variance')

    @api.depends('standard_material_cost', 'standard_labor_cost', 'standard_overhead_cost')
    def _compute_std_total(self):
        for rec in self:
            rec.total_standard_cost = (rec.standard_material_cost + rec.standard_labor_cost +
                rec.standard_overhead_cost)

    @api.depends('material_cost', 'standard_material_cost',
                 'labor_cost', 'standard_labor_cost',
                 'overhead_cost', 'standard_overhead_cost')
    def _compute_variances(self):
        for rec in self:
            rec.material_variance = rec.material_cost - rec.standard_material_cost
            rec.labor_variance = rec.labor_cost - rec.standard_labor_cost
            rec.overhead_variance = rec.overhead_cost - rec.standard_overhead_cost
            rec.total_variance = (rec.material_variance + rec.labor_variance +
                rec.overhead_variance)


class TapisSaleCostExt(models.Model):
    _inherit = 'tapis.sale'

    material_cost = fields.Float(string='Material Cost', readonly=True)
    labor_cost = fields.Float(string='Labor Cost', readonly=True)
    overhead_cost = fields.Float(string='Overhead Cost', readonly=True)
    gross_margin_percent = fields.Float(compute='_compute_gross_margin', store=True,
        string='Gross Margin %')
    gross_profit = fields.Float(compute='_compute_gross_margin', store=True,
        string='Gross Profit')

    @api.depends('total_price', 'material_cost', 'labor_cost', 'overhead_cost')
    def _compute_gross_margin(self):
        for rec in self:
            total_cost = rec.material_cost + rec.labor_cost + rec.overhead_cost
            rec.gross_profit = rec.total_price - total_cost
            rec.gross_margin_percent = (rec.gross_profit / rec.total_price * 100.0) \
                if rec.total_price else 0.0


class TapisProjectCostExt(models.Model):
    _inherit = 'tapis.project'

    total_revenue = fields.Float(string='Total Revenue', default=0.0)
    total_material_cost = fields.Float(string='Total Material Cost', default=0.0)
    total_labor_cost = fields.Float(string='Total Labor Cost', default=0.0)
    total_overhead_cost = fields.Float(string='Total Overhead Cost', default=0.0)
    gross_profit = fields.Float(compute='_compute_project_profit', store=True,
        string='Gross Profit')
    margin_percent = fields.Float(compute='_compute_project_profit', store=True,
        string='Margin %')
    roi_percent = fields.Float(compute='_compute_project_profit', store=True,
        string='ROI %')

    @api.depends('total_revenue', 'total_material_cost', 'total_labor_cost',
                 'total_overhead_cost', 'actual_cost')
    def _compute_project_profit(self):
        for rec in self:
            tc = rec.total_material_cost + rec.total_labor_cost + rec.total_overhead_cost
            rec.gross_profit = rec.total_revenue - tc
            rec.margin_percent = (rec.gross_profit / rec.total_revenue * 100.0) \
                if rec.total_revenue else 0.0
            total_invested = tc + rec.actual_cost
            rec.roi_percent = (rec.gross_profit / total_invested * 100.0) \
                if total_invested else 0.0
