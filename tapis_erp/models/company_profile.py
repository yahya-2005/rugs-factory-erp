from odoo import models, fields, api


class CompanyProfile(models.Model):
    _name = 'tapis.company.profile'
    _description = 'Company Profile'
    _rec_name = 'legal_name'
    _sql_constraints = [
        ('company_unique', 'UNIQUE(company_id)', 'Each company can only have one profile.'),
    ]

    company_id = fields.Many2one('res.company', string='Company', required=True)
    legal_name = fields.Char(required=True)
    trade_name = fields.Char()
    tax_id = fields.Char(string='Tax ID')
    registration_number = fields.Char()
    industry = fields.Char()
    phone = fields.Char()
    email = fields.Char()
    website = fields.Char()
    logo = fields.Binary(string='Company Logo', attachment=True)
    address = fields.Text()
    currency_id = fields.Many2one('res.currency', string='Currency')
    fiscal_year_start_month = fields.Integer(string='Fiscal Year Start Month', default=1)

    warehouse_ids = fields.One2many('tapis.warehouse', 'company_id', string='Warehouses')
    employee_ids = fields.One2many('tapis.employee', 'company_id', string='Employees')

    revenue_ytd = fields.Float(compute='_compute_financial_kpis', string='Revenue YTD')
    expenses_ytd = fields.Float(compute='_compute_financial_kpis', string='Expenses YTD')
    net_profit_ytd = fields.Float(compute='_compute_financial_kpis', string='Net Profit YTD')

    def _compute_financial_kpis(self):
        today = fields.Date.today()
        for rec in self:
            fiscal_start = today.replace(month=rec.fiscal_year_start_month or 1, day=1)
            if today < fiscal_start:
                fiscal_start = fiscal_start.replace(year=fiscal_start.year - 1)
            domain = [('company_id', '=', rec.company_id.id), ('invoice_date', '>=', fiscal_start)]
            invoices = self.env['tapis.invoice'].search(domain + [('state', '=', 'posted')])
            rec.revenue_ytd = sum(invoices.mapped('amount_total'))
            rec.expenses_ytd = sum(invoices.filtered(lambda i: i.amount_total < 0).mapped('amount_total'))
            rec.net_profit_ytd = rec.revenue_ytd - abs(rec.expenses_ytd)
