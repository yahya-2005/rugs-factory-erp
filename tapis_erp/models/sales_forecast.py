from odoo import _, models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta, datetime, date
from dateutil.relativedelta import relativedelta
import math


class TapisSalesForecast(models.Model):
    _name = 'tapis.sales.forecast'
    _description = 'Sales Forecast'
    _inherit = ['mail.thread']
    _order = 'generated_date desc, id desc'

    name = fields.Char(required=True, readonly=True, default='New')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    forecast_type = fields.Selection([
        ('product', 'Product'),
        ('category', 'Category'),
        ('customer', 'Customer'),
        ('company', 'Company'),
    ], required=True, default='product', tracking=True)
    product_id = fields.Many2one('tapis.product', string='Product', tracking=True)
    category = fields.Selection([
        ('traditional', 'Traditional'),
        ('modern', 'Modern'),
        ('custom', 'Custom design'),
    ], string='Category', tracking=True)
    customer_id = fields.Many2one('tapis.customer', string='Customer', tracking=True)

    period_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], required=True, default='monthly')
    periods_ahead = fields.Integer(default=6, required=True)

    history_start_date = fields.Date()
    history_end_date = fields.Date()

    generated_date = fields.Datetime(readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('approved', 'Approved'),
    ], default='draft', tracking=True)
    method = fields.Selection([
        ('moving_average', 'Moving Average'),
        ('weighted_average', 'Weighted Average'),
        ('exponential_smoothing', 'Exponential Smoothing'),
        ('seasonal_index', 'Seasonal Index'),
    ], default='moving_average', required=True, tracking=True)

    confidence_percent = fields.Float(string='Confidence %', readonly=True)
    accuracy_percent = fields.Float(string='Accuracy %', readonly=True)

    total_forecast_qty = fields.Float(compute='_compute_totals', store=True)
    total_forecast_revenue = fields.Float(compute='_compute_totals', store=True)

    line_ids = fields.One2many('tapis.sales.forecast.line', 'forecast_id', string='Forecast Lines')
    notes = fields.Text()
    charts_qty_html = fields.Html(compute='_render_charts_qty', sanitize=False, sanitize_tags=False)
    charts_revenue_html = fields.Html(compute='_render_charts_revenue', sanitize=False, sanitize_tags=False)

    @api.depends('line_ids', 'line_ids.forecast_qty', 'line_ids.forecast_revenue')
    def _compute_totals(self):
        for rec in self:
            rec.total_forecast_qty = sum(rec.line_ids.mapped('forecast_qty'))
            rec.total_forecast_revenue = sum(rec.line_ids.mapped('forecast_revenue'))

    def action_generate_forecast(self):
        for rec in self:
            rec._generate_forecast()

    def action_approve_forecast(self):
        for rec in self:
            if rec.state != 'generated':
                raise UserError(_('Only generated forecasts can be approved.'))
            rec.state = 'approved'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_create_procurement_plan(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved forecasts can create procurement plans.'))

    def action_create_production_plan(self):
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved forecasts can create production plans.'))

    def _get_sales_domain(self):
        self.ensure_one()
        domain = [('state', '=', 'delivered')]
        if self.forecast_type == 'product' and self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.forecast_type == 'customer' and self.customer_id:
            domain.append(('customer_id', '=', self.customer_id.id))
        if self.forecast_type == 'category' and self.category:
            products = self.env['tapis.product'].search([('category', '=', self.category)])
            domain.append(('product_id', 'in', products.ids))
        if self.history_start_date:
            domain.append(('order_date', '>=', self.history_start_date))
        if self.history_end_date:
            domain.append(('order_date', '<=', self.history_end_date + timedelta(days=1)))
        return domain

    def _period_key(self, dt):
        if self.period_type == 'monthly':
            return dt.strftime('%Y-%m')
        elif self.period_type == 'quarterly':
            q = (dt.month - 1) // 3 + 1
            return '%s-Q%s' % (dt.year, q)
        else:
            return str(dt.year)

    def _period_start_date(self, key):
        if self.period_type == 'monthly':
            return datetime.strptime(key + '-01', '%Y-%m-%d').date()
        elif self.period_type == 'quarterly':
            parts = key.split('-Q')
            year = int(parts[0])
            q = int(parts[1])
            month = (q - 1) * 3 + 1
            return date(year, month, 1)
        else:
            return date(int(key), 1, 1)

    def _next_period_key(self, key, count=1):
        dt = self._period_start_date(key)
        if self.period_type == 'monthly':
            dt += relativedelta(months=count)
            return dt.strftime('%Y-%m')
        elif self.period_type == 'quarterly':
            dt += relativedelta(months=3 * count)
            q = (dt.month - 1) // 3 + 1
            return '%s-Q%s' % (dt.year, q)
        else:
            dt += relativedelta(years=count)
            return str(dt.year)

    def _build_historical_data(self):
        domain = self._get_sales_domain()
        sales = self.env['tapis.sale'].search(domain, order='order_date')
        if not sales:
            raise UserError(_('No historical sales data found for the selected criteria.'))
        period_map = {}
        for s in sales:
            if not s.order_date:
                continue
            od = s.order_date
            if isinstance(od, str):
                od = fields.Datetime.from_string(od)
            key = self._period_key(od)
            if key not in period_map:
                period_map[key] = {'qty': 0.0, 'revenue': 0.0, 'count': 0}
            period_map[key]['qty'] += s.quantity
            period_map[key]['revenue'] += s.total_price
            period_map[key]['count'] += 1

        sorted_keys = sorted(period_map.keys())
        data = []
        for k in sorted_keys:
            data.append({
                'key': k,
                'date': self._period_start_date(k),
                'qty': period_map[k]['qty'],
                'revenue': period_map[k]['revenue'],
            })
        return data

    def _avg_price_from_history(self, historical):
        total_qty = sum(h['qty'] for h in historical)
        total_rev = sum(h['revenue'] for h in historical)
        return total_rev / total_qty if total_qty else 0.0

    def _moving_average(self, values, n=3):
        if not values:
            return 0.0
        n = min(n, len(values))
        return sum(values[-n:]) / n

    def _weighted_average(self, values):
        if not values:
            return 0.0
        n = len(values)
        weights = list(range(1, n + 1))
        total_weight = sum(weights)
        return sum(v * w for v, w in zip(values, weights)) / total_weight

    def _exponential_smoothing(self, values, alpha=0.3):
        if not values:
            return 0.0
        forecast = values[0]
        for v in values[1:]:
            forecast = alpha * v + (1 - alpha) * forecast
        return forecast

    def _seasonal_indices(self, values_by_period):
        if not values_by_period:
            return {}
        if self.period_type == 'monthly':
            period_label = lambda k: k.split('-')[1]
        elif self.period_type == 'quarterly':
            period_label = lambda k: k.split('-Q')[1] if 'Q' in k else '1'
        else:
            return {}

        sub_periods = {}
        for key, val in values_by_period.items():
            sp = period_label(key)
            if sp not in sub_periods:
                sub_periods[sp] = []
            sub_periods[sp].append(val)

        grand_avg = sum(values_by_period.values()) / len(values_by_period) if values_by_period else 1.0
        indices = {}
        for sp, vals in sub_periods.items():
            indices[sp] = (sum(vals) / len(vals)) / grand_avg if grand_avg else 1.0
        return indices

    def _generate_forecast(self):
        self.ensure_one()
        historical = self._build_historical_data()
        self.history_start_date = historical[0]['date']
        self.history_end_date = historical[-1]['date']

        avg_price = self._avg_price_from_history(historical)
        qty_series = [h['qty'] for h in historical]
        rev_series = [h['revenue'] for h in historical]

        last_key = historical[-1]['key']
        forecast_lines_data = []

        for period in historical:
            forecast_lines_data.append({
                'sequence': len(forecast_lines_data) + 1,
                'forecast_date': period['date'],
                'historical_qty': period['qty'],
                'historical_revenue': period['revenue'],
                'forecast_qty': 0.0,
                'forecast_revenue': 0.0,
            })

        for i in range(1, self.periods_ahead + 1):
            next_key = self._next_period_key(last_key, i)
            next_date = self._period_start_date(next_key)

            if self.method == 'moving_average':
                f_qty = self._moving_average(qty_series, 3)
                f_rev = self._moving_average(rev_series, 3)
            elif self.method == 'weighted_average':
                f_qty = self._weighted_average(qty_series)
                f_rev = self._weighted_average(rev_series)
            elif self.method == 'exponential_smoothing':
                f_qty = self._exponential_smoothing(qty_series)
                f_rev = self._exponential_smoothing(rev_series)
            elif self.method == 'seasonal_index':
                hist_dict = {h['key']: h['qty'] for h in historical}
                rev_dict = {h['key']: h['revenue'] for h in historical}
                indices = self._seasonal_indices(hist_dict)
                rev_indices = self._seasonal_indices(rev_dict)

                if self.period_type == 'monthly':
                    sp = next_key.split('-')[1]
                elif self.period_type == 'quarterly':
                    sp = next_key.split('-Q')[1] if 'Q' in next_key else '1'
                else:
                    sp = '1'

                base_qty = self._moving_average(qty_series, 3)
                base_rev = self._moving_average(rev_series, 3)
                si = indices.get(sp, 1.0)
                ri = rev_indices.get(sp, 1.0)
                f_qty = base_qty * si
                f_rev = base_rev * ri
            else:
                f_qty = 0.0
                f_rev = 0.0

            qty_series.append(f_qty)
            rev_series.append(f_rev)

            forecast_lines_data.append({
                'sequence': len(forecast_lines_data) + 1,
                'forecast_date': next_date,
                'historical_qty': 0.0,
                'historical_revenue': 0.0,
                'forecast_qty': f_qty,
                'forecast_revenue': f_rev,
            })

        self.line_ids.unlink()
        for line_data in forecast_lines_data:
            fq = line_data['forecast_qty']
            f_line = self.env['tapis.sales.forecast.line'].create({
                'forecast_id': self.id,
                'sequence': line_data['sequence'],
                'forecast_date': line_data['forecast_date'],
                'historical_qty': line_data['historical_qty'],
                'historical_revenue': line_data['historical_revenue'],
                'forecast_qty': fq,
                'forecast_revenue': line_data['forecast_revenue'],
            })
            stock = 0.0
            produced = 0.0
            if self.forecast_type == 'product' and self.product_id:
                stock = self.product_id.stock_qty
                produced = self.env['tapis.production'].search_count([
                    ('product_id', '=', self.product_id.id),
                    ('state', '=', 'done'),
                ])
            f_line.recommended_procurement_qty = max(fq - stock, 0.0)
            f_line.recommended_production_qty = max(fq - produced, 0.0)

            std = fq * 0.15
            f_line.lower_bound_qty = max(fq - 2 * std, 0.0)
            f_line.upper_bound_qty = fq + 2 * std
            f_line.confidence_percent = 95.0

        self.generated_date = fields.Datetime.now()
        self._compute_accuracy(historical, forecast_lines_data)
        self.state = 'generated'
        self.message_post(body=_('Forecast generated using %s method.') % dict(
            self._fields['method'].selection).get(self.method, self.method))
        template = self.env.ref('tapis_erp.email_template_forecast_generated', False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _compute_accuracy(self, historical, forecast_lines):
        self.ensure_one()
        if len(historical) < 2:
            self.accuracy_percent = 0.0
            self.confidence_percent = 0.0
            return

        actuals = [h['qty'] for h in historical]
        if len(actuals) < 2:
            self.accuracy_percent = 0.0
            self.confidence_percent = 0.0
            return

        self.accuracy_percent = self._compute_mape(actuals)
        self.confidence_percent = min(self.accuracy_percent, 99.0)

    def _compute_mape(self, actuals):
        n = len(actuals)
        if n < 2:
            return 0.0
        if self.method == 'moving_average':
            forecasts = []
            for i in range(1, n):
                window = actuals[max(0, i - 3):i]
                forecasts.append(sum(window) / len(window) if window else 0.0)
        elif self.method == 'weighted_average':
            forecasts = []
            for i in range(1, n):
                window = actuals[:i]
                forecasts.append(self._weighted_average(window))
        elif self.method == 'exponential_smoothing':
            forecasts = []
            alpha = 0.3
            if actuals:
                f = actuals[0]
                for i in range(1, n):
                    f = alpha * actuals[i - 1] + (1 - alpha) * f
                    forecasts.append(f)
        elif self.method == 'seasonal_index':
            forecasts = []
            for i in range(1, n):
                forecasts.append(sum(actuals[:i]) / i if i else 0.0)
        else:
            forecasts = [actuals[0]] * (n - 1)

        errors = []
        for i, f in enumerate(forecasts):
            a = actuals[i + 1] if (i + 1) < len(actuals) else actuals[-1]
            if a != 0:
                errors.append(abs((a - f) / a))
            else:
                errors.append(abs(f) if f != 0 else 0.0)

        mape = (sum(errors) / len(errors) * 100.0) if errors else 0.0
        return max(0.0, 100.0 - mape)


    def _render_charts_qty(self):
        for rec in self:
            lines = rec.line_ids.sorted('forecast_date')
            if not lines:
                rec.charts_qty_html = '<p class="text-muted">No data</p>'
                continue
            max_val = max(max(l.forecast_qty, l.historical_qty) for l in lines) or 1
            n = len(lines)
            bar_w = max(12, min(30, 480 // n)) if n else 20
            svg_w = n * (bar_w + 6) + 60
            svg_h = 200
            bars = ''
            for i, l in enumerate(lines):
                x = 50 + i * (bar_w + 6)
                hh = (l.historical_qty / max_val) * 140 if max_val else 0
                hf = (l.forecast_qty / max_val) * 140 if max_val else 0
                if l.historical_qty:
                    bars += '<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="#4e73df" rx="2"><title>Hist: %.1f</title></rect>' % (
                        x, 190 - hh, bar_w // 2 - 1, hh, l.historical_qty)
                if l.forecast_qty:
                    bars += '<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="#1cc88a" rx="2"><title>Fest: %.1f</title></rect>' % (
                        x + bar_w // 2 + 1, 190 - hf, bar_w // 2 - 1, hf, l.forecast_qty)
                bars += '<text x="%d" y="198" font-size="7" text-anchor="middle" fill="#666">%s</text>' % (
                    x + bar_w // 2, l.forecast_date.strftime('%y-%m') if l.forecast_date else '')
            rec.charts_qty_html = '''
            <div style="overflow: hidden;">
                <svg width="100%%" height="%d" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet">
                    <rect x="%d" y="5" width="8" height="8" fill="#4e73df"/><text x="%d" y="13" font-size="10" fill="#333">Historical</text>
                    <rect x="%d" y="5" width="8" height="8" fill="#1cc88a"/><text x="%d" y="13" font-size="10" fill="#333">Forecast</text>
                    %s
                </svg>
            </div>''' % (svg_h, svg_w, svg_h,
                svg_w - 180, svg_w - 170, svg_w - 80, svg_w - 70, bars)

    def _render_charts_revenue(self):
        for rec in self:
            lines = rec.line_ids.sorted('forecast_date')
            if not lines:
                rec.charts_revenue_html = '<p class="text-muted">No data</p>'
                continue
            max_val = max(max(l.forecast_revenue, l.historical_revenue) for l in lines) or 1
            n = len(lines)
            bar_w = max(12, min(30, 480 // n)) if n else 20
            svg_w = n * (bar_w + 6) + 60
            svg_h = 200
            bars = ''
            for i, l in enumerate(lines):
                x = 50 + i * (bar_w + 6)
                hh = (l.historical_revenue / max_val) * 140 if max_val else 0
                hf = (l.forecast_revenue / max_val) * 140 if max_val else 0
                if l.historical_revenue:
                    bars += '<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="#f6c23e" rx="2"><title>Hist: %.1f</title></rect>' % (
                        x, 190 - hh, bar_w // 2 - 1, hh, l.historical_revenue)
                if l.forecast_revenue:
                    bars += '<rect x="%d" y="%.1f" width="%d" height="%.1f" fill="#e74a3b" rx="2"><title>Fest: %.1f</title></rect>' % (
                        x + bar_w // 2 + 1, 190 - hf, bar_w // 2 - 1, hf, l.forecast_revenue)
                bars += '<text x="%d" y="198" font-size="7" text-anchor="middle" fill="#666">%s</text>' % (
                    x + bar_w // 2, l.forecast_date.strftime('%y-%m') if l.forecast_date else '')
            rec.charts_revenue_html = '''
            <div style="overflow: hidden;">
                <svg width="100%%" height="%d" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet">
                    <rect x="%d" y="5" width="8" height="8" fill="#f6c23e"/><text x="%d" y="13" font-size="10" fill="#333">Historical</text>
                    <rect x="%d" y="5" width="8" height="8" fill="#e74a3b"/><text x="%d" y="13" font-size="10" fill="#333">Forecast</text>
                    %s
                </svg>
            </div>''' % (svg_h, svg_w, svg_h,
                svg_w - 180, svg_w - 170, svg_w - 80, svg_w - 70, bars)


class TapisSalesForecastLine(models.Model):
    _name = 'tapis.sales.forecast.line'
    _description = 'Sales Forecast Line'
    _order = 'sequence, forecast_date'

    forecast_id = fields.Many2one('tapis.sales.forecast', required=True, ondelete='cascade')
    sequence = fields.Integer()
    forecast_date = fields.Date()

    historical_qty = fields.Float(string='Historical Qty')
    historical_revenue = fields.Float(string='Historical Revenue')
    forecast_qty = fields.Float(string='Forecast Qty')
    forecast_revenue = fields.Float(string='Forecast Revenue')

    recommended_procurement_qty = fields.Float(string='Recommended Procurement Qty')
    recommended_production_qty = fields.Float(string='Recommended Production Qty')

    lower_bound_qty = fields.Float(string='Lower Bound Qty')
    upper_bound_qty = fields.Float(string='Upper Bound Qty')
    confidence_percent = fields.Float(string='Confidence %', default=95.0)

    def name_get(self):
        return [(l.id, '%s - %s' % (l.forecast_id.name or '', l.forecast_date or '')) for l in self]
