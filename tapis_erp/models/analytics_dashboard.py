from odoo import models, fields, api
import json
from datetime import datetime, timedelta


class TapisAnalyticsDashboard(models.Model):
    _name = 'tapis.analytics.dashboard'
    _description = 'Analytics Dashboard'

    name = fields.Char(default="Analytics Dashboard")

    total_sales_revenue = fields.Float(compute='_compute_analytics')
    total_purchase_cost = fields.Float(compute='_compute_analytics')
    total_profit = fields.Float(compute='_compute_analytics')
    inventory_value = fields.Float(compute='_compute_analytics')
    total_customers = fields.Integer(compute='_compute_analytics')
    total_products = fields.Integer(compute='_compute_analytics')
    total_invoices = fields.Integer(compute='_compute_analytics')
    total_receivables = fields.Float(compute='_compute_analytics')

    monthly_sales_data = fields.Text(compute='_compute_analytics')
    monthly_purchase_data = fields.Text(compute='_compute_analytics')
    monthly_profit_data = fields.Text(compute='_compute_analytics')
    production_status_data = fields.Text(compute='_compute_analytics')
    top_products_data = fields.Text(compute='_compute_analytics')
    top_customers_data = fields.Text(compute='_compute_analytics')

    low_stock_count = fields.Integer(compute='_compute_analytics')
    low_stock_products_data = fields.Text(compute='_compute_analytics')
    unpaid_invoices_data = fields.Text(compute='_compute_analytics')
    pending_inspections_count = fields.Integer(compute='_compute_analytics')

    total_equipment = fields.Integer(compute='_compute_analytics')
    broken_equipment_count = fields.Integer(compute='_compute_analytics')
    under_maintenance_count = fields.Integer(compute='_compute_analytics')
    total_maintenance_cost = fields.Float(compute='_compute_analytics')
    overdue_maintenance_count = fields.Integer(compute='_compute_analytics')
    total_downtime_hours = fields.Float(compute='_compute_analytics')

    maintenance_monthly_cost_data = fields.Text(compute='_compute_analytics')
    maintenance_status_data = fields.Text(compute='_compute_analytics')
    total_projects = fields.Integer(compute='_compute_analytics')
    active_projects = fields.Integer(compute='_compute_analytics')
    total_tasks = fields.Integer(compute='_compute_analytics')
    overdue_tasks = fields.Integer(compute='_compute_analytics')
    tasks_in_review = fields.Integer(compute='_compute_analytics')
    total_timesheet_hours = fields.Float(compute='_compute_analytics')

    charts_html = fields.Html(compute='_render_charts_html', sanitize=False, sanitize_tags=False)
    low_stock_html = fields.Html(compute='_render_low_stock_html', sanitize=False, sanitize_tags=False)
    unpaid_html = fields.Html(compute='_render_unpaid_html', sanitize=False, sanitize_tags=False)

    def _compute_analytics(self):
        for rec in self:
            now = fields.Datetime.now()
            twelve_months_ago = now - timedelta(days=365)

            sales = self.env['tapis.sale'].search([('state', '=', 'delivered')])
            purchases = self.env['tapis.purchase'].search([('state', '=', 'received')])
            products = self.env['tapis.product'].search([])
            customers = self.env['tapis.customer'].search([])
            invoices = self.env['tapis.invoice'].search([('state', '=', 'posted')])

            rec.total_products = len(products)
            rec.total_customers = len(customers)
            rec.total_invoices = len(invoices)

            rec.total_sales_revenue = sum(sales.mapped('total_price'))
            rec.total_purchase_cost = sum(purchases.mapped('total_price'))
            rec.inventory_value = sum(p.stock_qty * p.cost for p in products)
            rec.total_profit = sum(sales.mapped('profit_amount'))

            rec.total_receivables = sum(
                i.amount_due for i in invoices
                if i.payment_status in ('unpaid', 'partial')
            )

            rec.monthly_sales_data = json.dumps(
                self._compute_monthly_sales(sales, twelve_months_ago, now)
            )
            rec.monthly_purchase_data = json.dumps(
                self._compute_monthly_purchases(purchases, twelve_months_ago, now)
            )
            rec.monthly_profit_data = json.dumps(
                self._compute_monthly_profit(sales, purchases, twelve_months_ago, now)
            )
            rec.production_status_data = json.dumps(
                self._compute_production_status()
            )
            rec.top_products_data = json.dumps(
                self._compute_top_products(sales)
            )
            rec.top_customers_data = json.dumps(
                self._compute_top_customers(sales)
            )

            low_stock = products.filtered(lambda p: p.stock_qty < 5)
            rec.low_stock_count = len(low_stock)
            rec.low_stock_products_data = json.dumps([
                {'name': p.name, 'stock': p.stock_qty, 'state': p.state}
                for p in low_stock[:10]
            ])

            unpaid = invoices.filtered(lambda i: i.payment_status in ('unpaid', 'partial'))
            rec.unpaid_invoices_data = json.dumps([
                {
                    'name': i.name,
                    'customer': i.customer_id.name or '',
                    'amount_due': i.amount_due,
                    'payment_status': i.payment_status,
                }
                for i in unpaid[:10]
            ])

            pending = self.env['tapis.quality.inspection'].search_count([
                ('state', '=', 'pending')
            ])
            rec.pending_inspections_count = pending

            equipment = self.env['tapis.equipment'].search([])
            rec.total_equipment = len(equipment)
            rec.broken_equipment_count = len(equipment.filtered(lambda e: e.state == 'broken'))
            rec.under_maintenance_count = len(equipment.filtered(lambda e: e.state == 'maintenance'))
            rec.total_maintenance_cost = sum(equipment.mapped('total_maintenance_cost'))
            rec.overdue_maintenance_count = len(equipment.filtered(lambda e: e.overdue_maintenance))
            rec.total_downtime_hours = sum(equipment.mapped('total_downtime_hours'))

            rec.maintenance_monthly_cost_data = json.dumps(
                self._compute_maintenance_monthly_cost(now, twelve_months_ago)
            )
            rec.maintenance_status_data = json.dumps(
                self._compute_maintenance_status()
            )
            projects = self.env['tapis.project'].search([])
            tasks = self.env['tapis.task'].search([])
            rec.total_projects = len(projects)
            rec.active_projects = len(projects.filtered(lambda p: p.state == 'in_progress'))
            rec.total_tasks = len(tasks)
            today = fields.Date.today()
            rec.overdue_tasks = len(tasks.filtered(
                lambda t: t.deadline and t.deadline < today and t.state not in ('done', 'cancelled')
            ))
            rec.tasks_in_review = len(tasks.filtered(lambda t: t.state == 'review'))
            rec.total_timesheet_hours = sum(tasks.mapped('actual_hours'))

    def _month_labels(self, start, end):
        labels = []
        current = start.replace(day=1)
        while current <= end:
            labels.append(current.strftime('%b'))
            current = (current + timedelta(days=32)).replace(day=1)
        return labels[:12]

    def _compute_monthly_sales(self, sales, start, end):
        months = {}
        current = start.replace(day=1)
        while current <= end:
            key = current.strftime('%Y-%m')
            months[key] = {'month': current.strftime('%b'), 'amount': 0.0}
            current = (current + timedelta(days=32)).replace(day=1)

        for sale in sales:
            if sale.order_date:
                dt = sale.order_date
                if hasattr(dt, 'date'):
                    dt = dt.date() if hasattr(dt, 'date') else dt
                else:
                    try:
                        dt = fields.Datetime.from_string(sale.order_date)
                    except Exception:
                        continue
                key = dt.strftime('%Y-%m')
                if key in months:
                    months[key]['amount'] += sale.total_price

        return [months[k] for k in sorted(months.keys())]

    def _compute_monthly_purchases(self, purchases, start, end):
        months = {}
        current = start.replace(day=1)
        while current <= end:
            key = current.strftime('%Y-%m')
            months[key] = {'month': current.strftime('%b'), 'amount': 0.0}
            current = (current + timedelta(days=32)).replace(day=1)

        for purchase in purchases:
            if purchase.received_date:
                dt = purchase.received_date
                if hasattr(dt, 'strftime'):
                    pass
                else:
                    try:
                        dt = fields.Date.from_string(purchase.received_date)
                    except Exception:
                        continue
                key = dt.strftime('%Y-%m')
                if key in months:
                    months[key]['amount'] += purchase.total_price

        return [months[k] for k in sorted(months.keys())]

    def _compute_monthly_profit(self, sales, purchases, start, end):
        months = {}
        current = start.replace(day=1)
        while current <= end:
            key = current.strftime('%Y-%m')
            months[key] = {'month': current.strftime('%b'), 'revenue': 0.0, 'cost': 0.0, 'profit': 0.0}
            current = (current + timedelta(days=32)).replace(day=1)

        for sale in sales:
            if sale.order_date:
                dt = sale.order_date
                try:
                    dt = fields.Datetime.from_string(sale.order_date)
                except Exception:
                    continue
                key = dt.strftime('%Y-%m')
                if key in months:
                    months[key]['revenue'] += sale.total_price
                    months[key]['profit'] += sale.profit_amount

        for purchase in purchases:
            if purchase.received_date:
                dt = purchase.received_date
                try:
                    dt = fields.Date.from_string(purchase.received_date)
                except Exception:
                    continue
                key = dt.strftime('%Y-%m')
                if key in months:
                    months[key]['cost'] += purchase.total_price

        return [months[k] for k in sorted(months.keys())]

    def _compute_production_status(self):
        production = self.env['tapis.production']
        records = production.search([])
        data = {
            'planned': 0,
            'in_progress': 0,
            'done': 0,
            'cancelled': 0,
        }
        for p in records:
            if p.state in data:
                data[p.state] += 1
        return [{'label': k.capitalize().replace('_', ' '), 'value': v} for k, v in data.items()]

    def _compute_top_products(self, sales):
        product_qty = {}
        for sale in sales:
            product = sale.product_id
            if product:
                if product.id not in product_qty:
                    product_qty[product.id] = {
                        'name': product.name,
                        'qty': 0,
                        'revenue': 0.0,
                    }
                product_qty[product.id]['qty'] += sale.quantity
                product_qty[product.id]['revenue'] += sale.total_price
        sorted_products = sorted(product_qty.values(), key=lambda x: x['revenue'], reverse=True)
        return sorted_products[:5]

    def _compute_top_customers(self, sales):
        customer_revenue = {}
        for sale in sales:
            customer = sale.customer_id
            if customer:
                if customer.id not in customer_revenue:
                    customer_revenue[customer.id] = {
                        'name': customer.name,
                        'revenue': 0.0,
                    }
                customer_revenue[customer.id]['revenue'] += sale.total_price
        sorted_customers = sorted(customer_revenue.values(), key=lambda x: x['revenue'], reverse=True)
        return sorted_customers[:5]

    def _compute_maintenance_monthly_cost(self, now, start):
        months = {}
        current = start.replace(day=1)
        while current <= now:
            key = current.strftime('%Y-%m')
            months[key] = {'month': current.strftime('%b'), 'cost': 0.0}
            current = (current + timedelta(days=32)).replace(day=1)

        orders = self.env['tapis.maintenance.order'].search([
            ('state', '=', 'done'),
            ('end_date', '>=', start),
        ])
        for order in orders:
            if order.end_date:
                try:
                    dt = fields.Datetime.from_string(order.end_date)
                except Exception:
                    continue
                key = dt.strftime('%Y-%m')
                if key in months:
                    months[key]['cost'] += order.total_cost
        return [months[k] for k in sorted(months.keys())]

    def _compute_maintenance_status(self):
        equipment = self.env['tapis.equipment'].search([])
        data = {'operational': 0, 'broken': 0, 'maintenance': 0, 'retired': 0}
        for e in equipment:
            if e.state in data:
                data[e.state] += 1
        return [{'label': k.capitalize().replace('_', ' '), 'value': v} for k, v in data.items()]

    def _render_charts_html(self):
        for rec in self:
            rec.charts_html = self._build_charts_html()

    def _build_charts_html(self):
        return self._build_svg_charts()

    def _build_svg_charts(self):
        html = '<div class="container-fluid"><div class="row">'
        html += self._svg_bar_card('Monthly Sales Trend', 'Sales (MAD)', '#4e73df',
            self.monthly_sales_data or '[]', 'amount')
        html += self._svg_bar_card('Monthly Purchase Trend', 'Purchases (MAD)', '#e74a3b',
            self.monthly_purchase_data or '[]', 'amount')
        html += '</div><div class="row">'
        html += self._svg_profit_card(self.monthly_profit_data or '[]')
        html += self._svg_donut_card('Production Status', self.production_status_data or '[]',
            ['#f6c23e', '#4e73df', '#1cc88a', '#858796'])
        html += '</div><div class="row">'
        html += self._svg_hbar_card('Top Products by Revenue', self.top_products_data or '[]', '#36b9cc')
        html += self._svg_hbar_card('Top Customers by Revenue', self.top_customers_data or '[]', '#f6c23e')
        html += '</div><div class="row">'
        html += self._svg_bar_card('Monthly Maintenance Cost', 'Cost (MAD)', '#36b9cc',
            self.maintenance_monthly_cost_data or '[]', 'cost')
        html += self._svg_donut_card('Equipment Status', self.maintenance_status_data or '[]',
            ['#1cc88a', '#e74a3b', '#f6c23e', '#858796'])
        html += '</div></div>'
        return html

    def _svg_bar_card(self, title, ylabel, color, json_data, amount_key):
        import json
        data = json.loads(json_data) if json_data else []
        if not data:
            return '<div class="col-lg-6 mb-4"><div class="card shadow"><div class="card-header"><h6>%s</h6></div><div class="card-body"><p class="text-muted">No data</p></div></div></div>' % title
        max_val = max(d.get(amount_key, 0) for d in data) or 1
        bar_w = max(30, min(60, 480 // len(data)))
        svg_w = len(data) * (bar_w + 10) + 60
        svg_h = 220
        bars = ''
        for i, d in enumerate(data):
            h = (d.get(amount_key, 0) / max_val) * 160
            x = 50 + i * (bar_w + 10)
            y = 200 - h
            bars += '<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="%s" rx="3"><title>%s: %.0f</title></rect>' % (
                x, y, bar_w, h, color, d.get('month', ''), d.get(amount_key, 0))
            bars += '<text x="%d" y="215" font-size="10" text-anchor="middle" fill="#666">%s</text>' % (
                x + bar_w // 2, d.get('month', ''))
        return '''
        <div class="col-lg-6 mb-4">
            <div class="card shadow h-100">
                <div class="card-header py-3"><h6 class="m-0 font-weight-bold" style="color:%s">%s</h6></div>
                <div class="card-body text-center" style="overflow: hidden;">
                    <svg width="100%%" height="%d" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet">
                        <line x1="45" y1="200" x2="%d" y2="200" stroke="#ddd" stroke-width="1"/>
                        <text x="40" y="20" font-size="11" fill="#999" text-anchor="end">%.0f</text>
                        <text x="40" y="105" font-size="11" fill="#999" text-anchor="end">%.0f</text>
                        <text x="40" y="195" font-size="11" fill="#999" text-anchor="end">0</text>
                        %s
                    </svg>
                </div>
            </div>
        </div>''' % (color, title, svg_h, svg_w, svg_h, 50 + len(data) * (bar_w + 10), max_val, max_val / 2, bars)

    def _svg_hbar_card(self, title, json_data, color):
        import json
        data = json.loads(json_data) if json_data else []
        if not data:
            return '<div class="col-lg-6 mb-4"><div class="card shadow"><div class="card-header"><h6>%s</h6></div><div class="card-body"><p class="text-muted">No data</p></div></div></div>' % title
        max_val = max(d.get('revenue', 0) for d in data) or 1
        bar_h = 24
        svg_h = len(data) * (bar_h + 8) + 30
        svg_w = 400
        bars = ''
        for i, d in enumerate(data[:8]):
            w = (d.get('revenue', 0) / max_val) * 280
            y = 20 + i * (bar_h + 8)
            name = (d.get('name', '')[:18] + '..') if len(d.get('name', '')) > 18 else d.get('name', '')
            bars += '<text x="5" y="%d" font-size="11" fill="#333">%s</text>' % (y + 16, name)
            bars += '<rect x="115" y="%d" width="%.1f" height="%d" fill="%s" rx="3"><title>%.0f</title></rect>' % (
                y, w, bar_h, color, d.get('revenue', 0))
            bars += '<text x="%.1f" y="%d" font-size="10" fill="#333">%.0f</text>' % (
                120 + w, y + 16, d.get('revenue', 0))
        return '''
        <div class="col-lg-6 mb-4">
            <div class="card shadow h-100">
                <div class="card-header py-3"><h6 class="m-0 font-weight-bold" style="color:%s">%s</h6></div>
                <div class="card-body" style="overflow: hidden;">
                    <svg width="100%%" height="%d" viewBox="0 0 %d %d">%s</svg>
                </div>
            </div>
        </div>''' % (color, title, svg_h, svg_w, svg_h, bars)

    def _svg_profit_card(self, json_data):
        import json
        data = json.loads(json_data) if json_data else []
        if not data:
            return '<div class="col-lg-8 mb-4"><div class="card shadow"><div class="card-header"><h6>Monthly Profit Trend</h6></div><div class="card-body"><p class="text-muted">No data</p></div></div></div>'
        max_val = max(
            max(d.get('revenue', 0), d.get('cost', 0), d.get('profit', 0)) for d in data
        ) or 1
        gw = 560
        gh = 220
        n = len(data)
        spacing = max(30, min(50, gw // n))
        bars = ''
        for i, d in enumerate(data):
            x = 40 + i * spacing
            bh_r = (d.get('revenue', 0) / max_val) * 160
            bh_c = (d.get('cost', 0) / max_val) * 160
            bh_p = (d.get('profit', 0) / max_val) * 160
            bars += '<rect x="%d" y="%.1f" width="8" height="%.1f" fill="#1cc88a" rx="1"><title>Rev: %.0f</title></rect>' % (
                x - 10, 200 - bh_r, bh_r, d.get('revenue', 0))
            bars += '<rect x="%d" y="%.1f" width="8" height="%.1f" fill="#e74a3b" rx="1"><title>Cost: %.0f</title></rect>' % (
                x, 200 - bh_c, bh_c, d.get('cost', 0))
            bars += '<rect x="%d" y="%.1f" width="8" height="%.1f" fill="#4e73df" rx="1"><title>Profit: %.0f</title></rect>' % (
                x + 10, 200 - bh_p, bh_p, d.get('profit', 0))
            bars += '<text x="%d" y="215" font-size="9" text-anchor="middle" fill="#666">%s</text>' % (
                x + 4, d.get('month', ''))
        return '''
        <div class="col-lg-8 mb-4">
            <div class="card shadow h-100">
                <div class="card-header py-3"><h6 class="m-0 font-weight-bold text-success">Monthly Profit Trend</h6></div>
                <div class="card-body text-center" style="overflow: hidden;">
                    <svg width="100%%" height="%d" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet">
                        <line x1="35" y1="200" x2="%d" y2="200" stroke="#ddd"/>
                        <text x="30" y="20" font-size="10" fill="#999" text-anchor="end">%.0f</text>
                        <text x="30" y="105" font-size="10" fill="#999" text-anchor="end">%.0f</text>
                        <text x="30" y="195" font-size="10" fill="#999" text-anchor="end">0</text>
                        %s
                        <rect x="%d" y="5" width="8" height="8" fill="#1cc88a"/><text x="%d" y="13" font-size="10" fill="#333">Revenue</text>
                        <rect x="%d" y="5" width="8" height="8" fill="#e74a3b"/><text x="%d" y="13" font-size="10" fill="#333">Cost</text>
                        <rect x="%d" y="5" width="8" height="8" fill="#4e73df"/><text x="%d" y="13" font-size="10" fill="#333">Profit</text>
                    </svg>
                </div>
            </div>
        </div>''' % (gh, gw, gh, 40 + (n - 1) * spacing + 20, max_val, max_val / 2, bars,
            40 + n * spacing, 48 + n * spacing, 40 + n * spacing + 60, 48 + n * spacing + 60,
            40 + n * spacing + 120, 48 + n * spacing + 120)

    def _svg_donut_card(self, title, json_data, colors):
        import json, math
        data = json.loads(json_data) if json_data else []
        if not data:
            return '<div class="col-lg-4 mb-4"><div class="card shadow"><div class="card-header"><h6>%s</h6></div><div class="card-body"><p class="text-muted">No data</p></div></div></div>' % title
        total = sum(d.get('value', 0) for d in data) or 1
        cx, cy, r, ir = 100, 100, 70, 45
        svg_w, svg_h = 200, 200
        paths = ''
        angle = -90
        legend = ''
        for i, d in enumerate(data):
            val = d.get('value', 0)
            pct = val / total
            a = pct * 360
            end_angle = angle + a
            rad = math.radians
            x1 = cx + r * math.cos(rad(angle))
            y1 = cy + r * math.sin(rad(angle))
            x2 = cx + r * math.cos(rad(end_angle))
            y2 = cy + r * math.sin(rad(end_angle))
            x3 = cx + ir * math.cos(rad(end_angle))
            y3 = cy + ir * math.sin(rad(end_angle))
            x4 = cx + ir * math.cos(rad(angle))
            y4 = cy + ir * math.sin(rad(angle))
            large = 1 if a > 180 else 0
            paths += '<path d="M %.1f %.1f A %.1f %.1f 0 %d 1 %.1f %.1f L %.1f %.1f A %.1f %.1f 0 %d 0 %.1f %.1f Z" fill="%s"><title>%s: %d (%.0f%%)</title></path>' % (
                x1, y1, r, r, large, x2, y2, x3, y3, ir, ir, large, x4, y4,
                colors[i % len(colors)], d.get('label', ''), val, pct * 100)
            angle = end_angle
            lx = 20 if i % 2 == 0 else 120
            ly = 160 + (i // 2) * 18
            legend += '<rect x="%d" y="%d" width="10" height="10" fill="%s"/><text x="%d" y="%d" font-size="10" fill="#333">%s (%d)</text>' % (
                lx, ly, colors[i % len(colors)], lx + 14, ly + 9, d.get('label', ''), val)
        return '''
        <div class="col-lg-4 mb-4">
            <div class="card shadow h-100">
                <div class="card-header py-3"><h6 class="m-0 font-weight-bold text-info">%s</h6></div>
                <div class="card-body text-center" style="overflow: hidden;">
                    <svg width="100%%" height="%d" viewBox="0 0 %d %d">%s%s</svg>
                </div>
            </div>
        </div>''' % (title, svg_h, svg_w, svg_h, paths, legend)

    def _render_low_stock_html(self):
        for rec in self:
            data = json.loads(rec.low_stock_products_data or '[]')
            if not data:
                rec.low_stock_html = '<p class="text-muted">No low stock products.</p>'
                continue
            html = '<table class="table table-sm table-striped"><thead><tr><th>Product</th><th>Stock</th><th>State</th></tr></thead><tbody>'
            for row in data:
                html += '<tr><td>%s</td><td>%s</td><td>%s</td></tr>' % (row.get('name', ''), row.get('stock', 0), row.get('state', ''))
            html += '</tbody></table>'
            rec.low_stock_html = html

    def _render_unpaid_html(self):
        for rec in self:
            data = json.loads(rec.unpaid_invoices_data or '[]')
            if not data:
                rec.unpaid_html = '<p class="text-muted">No unpaid invoices.</p>'
                continue
            html = '<table class="table table-sm table-striped"><thead><tr><th>Invoice</th><th>Customer</th><th>Amount Due</th><th>Status</th></tr></thead><tbody>'
            for row in data:
                html += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                    row.get('name', ''), row.get('customer', ''), row.get('amount_due', 0), row.get('payment_status', ''))
            html += '</tbody></table>'
            rec.unpaid_html = html

    def action_refresh(self):
        self.invalidate_cache()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tapis.analytics.dashboard',
            'view_mode': 'form',
            'view_id': self.env.ref('tapis_erp.view_analytics_dashboard_form').id,
            'target': 'current',
            'res_id': self.id,
        }

    def action_view_sales(self):
        return self._open_action('tapis.sale', 'Sales', 'tree,form,graph')

    def action_view_purchases(self):
        return self._open_action('tapis.purchase', 'Purchases', 'tree,form,graph')

    def action_view_products(self):
        return self._open_action('tapis.product', 'Products', 'tree,form,kanban')

    def action_view_customers(self):
        return self._open_action('tapis.customer', 'Customers', 'tree,form')

    def action_view_invoices(self):
        return self._open_action('tapis.invoice', 'Invoices', 'tree,form')

    def action_view_low_stock(self):
        return self._open_action('tapis.product', 'Low Stock Products', 'tree,form,kanban',
                                 domain=[('stock_qty', '<', 5)])

    def action_view_productions(self):
        return self._open_action('tapis.production', 'Productions', 'tree,form,graph')

    def action_view_equipment(self):
        return self._open_action('tapis.equipment', 'Equipment', 'tree,form')

    def action_view_maintenance(self):
        return self._open_action('tapis.maintenance.order', 'Maintenance Orders', 'tree,form')
    def action_view_projects(self):
        return self._open_action('tapis.project', 'Projects', 'kanban,tree,form')
    def action_view_tasks(self):
        return self._open_action('tapis.task', 'Tasks', 'kanban,tree,form')
    def action_view_timesheets(self):
        return self._open_action('tapis.task.timesheet', 'Timesheets', 'tree,form')
    def action_view_quality(self):
        return self._open_action('tapis.quality.inspection', 'Quality Inspections', 'tree,form')

    def _open_action(self, model, name, view_mode, domain=None):
        action = {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': view_mode,
            'target': 'current',
        }
        if domain:
            action['domain'] = domain
        return action
