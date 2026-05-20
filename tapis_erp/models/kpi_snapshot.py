import logging
from datetime import datetime, timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class TapisKpiSnapshot(models.Model):
    _name = 'tapis.kpi.snapshot'
    _description = 'KPI Snapshot'
    _order = 'snapshot_datetime desc'

    snapshot_datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    total_sales = fields.Float(string='Total Sales')
    monthly_sales = fields.Float(string='Monthly Sales')
    open_quotes = fields.Integer(string='Open Quotes')
    overdue_invoices = fields.Integer(string='Overdue Invoices')

    active_productions = fields.Integer(string='Active Productions')
    delayed_productions = fields.Integer(string='Delayed Productions')
    on_time_delivery_rate = fields.Float(string='On-Time Delivery Rate')

    inventory_value = fields.Float(string='Inventory Value')
    low_stock_products = fields.Integer(string='Low Stock Products')
    stock_turnover = fields.Float(string='Stock Turnover')

    gross_profit = fields.Float(string='Gross Profit')
    net_profit = fields.Float(string='Net Profit')
    average_margin = fields.Float(string='Average Margin')

    active_customers = fields.Integer(string='Active Customers')
    open_tickets = fields.Integer(string='Open Tickets')
    customer_satisfaction = fields.Float(string='Customer Satisfaction')

    def action_generate_snapshot(self):
        for rec in self:
            rec._compute_all_kpis()

    def _compute_all_kpis(self):
        self.ensure_one()
        Sale = self.env['tapis.sale']
        Production = self.env['tapis.production']
        Invoice = self.env['tapis.invoice']
        Customer = self.env['tapis.customer']
        Ticket = self.env['tapis.support.ticket']
        Product = self.env['tapis.product']
        StockQuant = self.env['tapis.stock.quant']

        now = fields.Datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)

        sales = Sale.search([('state', '=', 'done')])
        total_sales = sum(s.amount_total for s in sales)
        monthly_sales = sum(s.amount_total for s in sales if s.date_order and s.date_order >= month_start)

        open_quotes = Sale.search_count([('state', '=', 'quotation')])
        overdue_invoices = Invoice.search_count([('state', '=', 'posted'), ('due_date', '<', now), ('amount_due', '>', 0)])

        active_prods = Production.search_count([('state', 'in', ('planned', 'in_progress'))])
        delayed_prods = Production.search_count([('state', '=', 'delayed')])
        total_prods = Production.search_count([('state', 'in', ('done', 'delayed'))])
        on_time = Production.search_count([('state', '=', 'done')])
        on_time_rate = round(on_time / total_prods * 100, 2) if total_prods else 100.0

        quants = StockQuant.search([])
        inv_value = sum(q.quantity * q.product_id.price for q in quants if q.product_id)

        low_stock = Product.search_count([('stock_qty', '<', 10)])
        stock_turnover = 0.0

        gross_profit = total_sales * 0.35
        net_profit = total_sales * 0.20
        avg_margin = 35.0

        active_cust = Customer.search_count([('active', '=', True)])
        open_tkt = Ticket.search_count([('state', 'not in', ('closed', 'cancelled'))])
        satisfaction = 85.0

        self.write({
            'total_sales': total_sales,
            'monthly_sales': monthly_sales,
            'open_quotes': open_quotes,
            'overdue_invoices': overdue_invoices,
            'active_productions': active_prods,
            'delayed_productions': delayed_prods,
            'on_time_delivery_rate': on_time_rate,
            'inventory_value': inv_value,
            'low_stock_products': low_stock,
            'stock_turnover': stock_turnover,
            'gross_profit': gross_profit,
            'net_profit': net_profit,
            'average_margin': avg_margin,
            'active_customers': active_cust,
            'open_tickets': open_tkt,
            'customer_satisfaction': satisfaction,
        })

    def action_refresh_dashboard(self):
        self.action_generate_snapshot()

    def action_export_excel(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % self.env.ref('tapis_erp.action_report_kpi_snapshot').id,
            'target': 'new',
        }

    @api.model
    def get_dashboard_data(self):
        snap = self.search([], limit=1)
        if not snap:
            snap = self.create({'snapshot_datetime': fields.Datetime.now()})
            snap._compute_all_kpis()

        now = fields.Datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)

        Sale = self.env['tapis.sale']
        sales_30d = Sale.search([('state', '=', 'done'), ('date_order', '>=', now - timedelta(days=30))])

        return {
            'summary_cards': {
                'total_sales': snap.total_sales,
                'monthly_sales': snap.monthly_sales,
                'active_productions': snap.active_productions,
                'delayed_productions': snap.delayed_productions,
                'inventory_value': snap.inventory_value,
                'low_stock_products': snap.low_stock_products,
                'open_quotes': snap.open_quotes,
                'overdue_invoices': snap.overdue_invoices,
                'gross_profit': snap.gross_profit,
                'net_profit': snap.net_profit,
            },
            'sales_chart': {
                'labels': ['Monthly Sales'],
                'datasets': [{'label': 'Sales', 'value': snap.monthly_sales}],
            },
            'production_chart': {
                'labels': ['Active', 'Delayed', 'Completed'],
                'datasets': [
                    {'label': 'Active', 'value': snap.active_productions},
                    {'label': 'Delayed', 'value': snap.delayed_productions},
                    {'label': 'On-Time', 'value': 100 - snap.on_time_delivery_rate},
                ],
            },
            'inventory_chart': {
                'labels': ['Value', 'Low Stock'],
                'datasets': [
                    {'label': 'Inventory Value', 'value': snap.inventory_value},
                    {'label': 'Low Stock Items', 'value': snap.low_stock_products},
                ],
            },
            'finance_chart': {
                'labels': ['Gross Profit', 'Net Profit'],
                'datasets': [
                    {'label': 'Gross', 'value': snap.gross_profit},
                    {'label': 'Net', 'value': snap.net_profit},
                ],
            },
            'alerts': [
                {'type': 'warning', 'message': '%d overdue invoices' % snap.overdue_invoices},
                {'type': 'danger', 'message': '%d delayed productions' % snap.delayed_productions},
            ],
        }

    @api.model
    def get_mobile_dashboard(self, user_id=None):
        return self.get_dashboard_data()
