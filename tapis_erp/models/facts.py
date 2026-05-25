import logging
import csv
import io
from datetime import datetime, timedelta
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DwFactSales(models.Model):
    _name = 'tapis.dw.fact_sales'
    _description = 'Sales Fact'
    _order = 'date_key desc'

    date_key = fields.Integer(string='Date Key', index=True)
    product_key = fields.Integer(string='Product Key', index=True)
    customer_key = fields.Integer(string='Customer Key', index=True)
    company_key = fields.Integer(string='Company Key', index=True)
    quantity = fields.Float(string='Quantity')
    unit_price = fields.Float(string='Unit Price')
    revenue = fields.Float(string='Revenue')
    cost = fields.Float(string='Cost')
    gross_profit = fields.Float(string='Gross Profit')
    margin_percent = fields.Float(string='Margin %')
    discount_amount = fields.Float(string='Discount Amount', default=0.0)

    source_id = fields.Integer(string='Source Sale ID', index=True)

    _sql_constraints = [
        ('check_quantity', 'CHECK(quantity >= 0)', 'Quantity cannot be negative.'),
    ]


class DwFactInventory(models.Model):
    _name = 'tapis.dw.fact_inventory'
    _description = 'Inventory Fact'
    _order = 'date_key desc'

    date_key = fields.Integer(string='Date Key', index=True)
    product_key = fields.Integer(string='Product Key', index=True)
    company_key = fields.Integer(string='Company Key', index=True)
    on_hand_qty = fields.Float(string='On Hand Qty')
    reserved_qty = fields.Float(string='Reserved Qty')
    available_qty = fields.Float(string='Available Qty')
    inventory_value = fields.Float(string='Inventory Value')
    reorder_point = fields.Float(string='Reorder Point')
    stockout_risk = fields.Selection([
        ('none', 'None'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Stockout Risk', default='none')

    source_id = fields.Integer(string='Source Product ID', index=True)


class DwFactProduction(models.Model):
    _name = 'tapis.dw.fact_production'
    _description = 'Production Fact'
    _order = 'date_key desc'

    date_key = fields.Integer(string='Date Key', index=True)
    product_key = fields.Integer(string='Product Key', index=True)
    company_key = fields.Integer(string='Company Key', index=True)
    resource_key = fields.Integer(string='Resource Key', index=True)
    produced_qty = fields.Float(string='Produced Qty')
    planned_hours = fields.Float(string='Planned Hours')
    actual_hours = fields.Float(string='Actual Hours')
    efficiency_percent = fields.Float(string='Efficiency %')
    delay_days = fields.Integer(string='Delay Days', default=0)
    material_cost = fields.Float(string='Material Cost')
    labor_cost = fields.Float(string='Labor Cost')
    overhead_cost = fields.Float(string='Overhead Cost')

    source_id = fields.Integer(string='Source Production ID', index=True)


class DwFactFinance(models.Model):
    _name = 'tapis.dw.fact_finance'
    _description = 'Finance Fact'
    _order = 'date_key desc'

    date_key = fields.Integer(string='Date Key', index=True)
    customer_key = fields.Integer(string='Customer Key', index=True)
    company_key = fields.Integer(string='Company Key', index=True)
    revenue = fields.Float(string='Revenue')
    expenses = fields.Float(string='Expenses')
    gross_profit = fields.Float(string='Gross Profit')
    net_profit = fields.Float(string='Net Profit')
    outstanding_receivables = fields.Float(string='Outstanding Receivables')
    overdue_amount = fields.Float(string='Overdue Amount')

    source_id = fields.Integer(string='Source Invoice ID', index=True)


class DwFactQuality(models.Model):
    _name = 'tapis.dw.fact_quality'
    _description = 'Quality Fact'
    _order = 'date_key desc'

    date_key = fields.Integer(string='Date Key', index=True)
    product_key = fields.Integer(string='Product Key', index=True)
    company_key = fields.Integer(string='Company Key', index=True)
    inspections_count = fields.Integer(string='Inspections')
    defects_count = fields.Integer(string='Defects')
    defect_rate = fields.Float(string='Defect Rate')
    quality_score = fields.Float(string='Quality Score')

    source_id = fields.Integer(string='Source Inspection ID', index=True)


class DwFactSupport(models.Model):
    _name = 'tapis.dw.fact_support'
    _description = 'Support Fact'
    _order = 'date_key desc'

    date_key = fields.Integer(string='Date Key', index=True)
    customer_key = fields.Integer(string='Customer Key', index=True)
    company_key = fields.Integer(string='Company Key', index=True)
    tickets_count = fields.Integer(string='Tickets')
    resolution_hours = fields.Float(string='Resolution Hours')
    satisfaction_score = fields.Float(string='Satisfaction Score')

    source_id = fields.Integer(string='Source Ticket ID', index=True)


class DwInventorySnapshot(models.Model):
    _name = 'tapis.dw.snapshot_inventory'
    _description = 'Inventory Daily Snapshot'
    _order = 'snapshot_date desc'

    snapshot_date = fields.Date(required=True, index=True)
    product_id = fields.Many2one('tapis.product', string='Product')
    on_hand_qty = fields.Float()
    reserved_qty = fields.Float()
    available_qty = fields.Float()
    inventory_value = fields.Float()

    _sql_constraints = [
        ('snapshot_date_product_unique', 'unique(snapshot_date, product_id)',
         'Only one snapshot per product per date.'),
    ]


class DwKpiSnapshotHistory(models.Model):
    _name = 'tapis.dw.snapshot_kpi'
    _description = 'KPI Daily Snapshot'
    _order = 'snapshot_date desc'

    snapshot_date = fields.Date(required=True, index=True)
    total_sales = fields.Float()
    monthly_sales = fields.Float()
    open_quotes = fields.Integer()
    overdue_invoices = fields.Integer()
    active_productions = fields.Integer()
    delayed_productions = fields.Integer()
    on_time_delivery_rate = fields.Float()
    inventory_value = fields.Float()
    low_stock_products = fields.Integer()
    gross_profit = fields.Float()
    net_profit = fields.Float()
    active_customers = fields.Integer()
    open_tickets = fields.Integer()

    _sql_constraints = [
        ('snapshot_date_unique', 'unique(snapshot_date)',
         'Only one KPI snapshot per date.'),
    ]


class DwFactEngine(models.Model):
    _name = 'tapis.dw.fact.engine'
    _description = 'Data Warehouse ETL Engine'
    _auto = False

    @api.model
    def extract_data(self):
        total = 0
        total += self._extract_products()
        total += self._extract_customers()
        total += self._extract_companies()
        total += self._extract_suppliers()
        total += self._extract_users()
        total += self._extract_resources()
        _logger.info('ETL extract: %d records extracted', total)
        return total

    @api.model
    def _extract_products(self):
        products = self.env['tapis.product'].sudo().search([])
        last_run = self._get_last_etl_time()
        if last_run:
            products = products.filtered(lambda p: p.write_date and p.write_date > last_run)
        return len(products)

    @api.model
    def _extract_customers(self):
        customers = self.env['tapis.customer'].sudo().search([])
        last_run = self._get_last_etl_time()
        if last_run:
            customers = customers.filtered(lambda c: c.write_date and c.write_date > last_run)
        return len(customers)

    @api.model
    def _extract_companies(self):
        return len(self.env['res.company'].sudo().search([]))

    @api.model
    def _extract_suppliers(self):
        suppliers = self.env['tapis.supplier'].sudo().search([])
        last_run = self._get_last_etl_time()
        if last_run:
            suppliers = suppliers.filtered(lambda s: s.write_date and s.write_date > last_run)
        return len(suppliers)

    @api.model
    def _extract_users(self):
        return len(self.env['res.users'].sudo().search([]))

    @api.model
    def _extract_resources(self):
        resources = self.env['tapis.production.resource'].sudo().search([])
        last_run = self._get_last_etl_time()
        if last_run:
            resources = resources.filtered(lambda r: r.write_date and r.write_date > last_run)
        return len(resources)

    @api.model
    def _get_last_etl_time(self):
        config = self.env['tapis.dw.config'].sudo().search([('incremental_load', '=', True)], limit=1)
        return config.last_etl_datetime if config else False

    @api.model
    def transform_data(self):
        total = 0
        total += self._transform_products()
        total += self._transform_customers()
        total += self._transform_suppliers()
        _logger.info('ETL transform: %d records transformed', total)
        return total

    @api.model
    def _transform_products(self):
        DimProduct = self.env['tapis.dw.dim_product'].sudo()
        Product = self.env['tapis.product'].sudo()
        products = Product.search([])
        changed = 0
        for prod in products:
            existing = DimProduct.search([('source_id', '=', prod.id), ('is_current', '=', True)], limit=1)
            attrs = {
                'name': prod.name,
                'code': prod.code or '',
                'category': prod.category or '',
                'tags': prod.tags or '',
                'standard_cost': prod.standard_cost or 0.0,
                'list_price': prod.price or 0.0,
                'uom': prod.uom or '',
            }
            if existing:
                needs_update = any(str(existing[f]) != str(attrs[f]) for f in attrs)
                if needs_update:
                    existing.write({'valid_to': fields.Datetime.now(), 'is_current': False})
                    max_key = DimProduct.search([], order='surrogate_key desc', limit=1)
                    next_key = (max_key.surrogate_key or 0) + 1
                    DimProduct.create({
                        'surrogate_key': next_key,
                        'source_id': prod.id,
                        'active': prod.active if hasattr(prod, 'active') else True,
                        'valid_from': fields.Datetime.now(),
                        'valid_to': False,
                        'is_current': True,
                        **attrs,
                    })
                    changed += 1
            else:
                max_key = DimProduct.search([], order='surrogate_key desc', limit=1)
                next_key = (max_key.surrogate_key or 0) + 1
                DimProduct.create({
                    'surrogate_key': next_key,
                    'source_id': prod.id,
                    'active': prod.active if hasattr(prod, 'active') else True,
                    'valid_from': fields.Datetime.now(),
                    'valid_to': False,
                    'is_current': True,
                    **attrs,
                })
                changed += 1
        return changed

    @api.model
    def _transform_customers(self):
        DimCustomer = self.env['tapis.dw.dim_customer'].sudo()
        Customer = self.env['tapis.customer'].sudo()
        customers = Customer.search([])
        changed = 0
        for cust in customers:
            existing = DimCustomer.search([('source_id', '=', cust.id), ('is_current', '=', True)], limit=1)
            attrs = {
                'name': cust.name,
                'email': cust.email or '',
                'phone': cust.phone or '',
                'address': cust.address or '',
                'city': cust.city or '',
                'country': cust.country or '',
                'segment': cust.segment or '',
                'credit_limit': cust.credit_limit or 0.0,
            }
            if existing:
                needs_update = any(str(existing[f]) != str(attrs[f]) for f in attrs)
                if needs_update:
                    existing.write({'valid_to': fields.Datetime.now(), 'is_current': False})
                    max_key = DimCustomer.search([], order='surrogate_key desc', limit=1)
                    next_key = (max_key.surrogate_key or 0) + 1
                    DimCustomer.create({
                        'surrogate_key': next_key,
                        'source_id': cust.id,
                        'active': True,
                        'valid_from': fields.Datetime.now(),
                        'valid_to': False,
                        'is_current': True,
                        **attrs,
                    })
                    changed += 1
            else:
                max_key = DimCustomer.search([], order='surrogate_key desc', limit=1)
                next_key = (max_key.surrogate_key or 0) + 1
                DimCustomer.create({
                    'surrogate_key': next_key,
                    'source_id': cust.id,
                    'active': True,
                    'valid_from': fields.Datetime.now(),
                    'valid_to': False,
                    'is_current': True,
                    **attrs,
                })
                changed += 1
        return changed

    @api.model
    def _transform_suppliers(self):
        DimSupplier = self.env['tapis.dw.dim_supplier'].sudo()
        Supplier = self.env['tapis.supplier'].sudo()
        suppliers = Supplier.search([])
        changed = 0
        for supp in suppliers:
            existing = DimSupplier.search([('source_id', '=', supp.id), ('is_current', '=', True)], limit=1)
            attrs = {
                'name': supp.name,
                'email': supp.email or '',
                'phone': supp.phone or '',
                'country': supp.country or '',
                'payment_terms': supp.payment_terms or '',
                'rating': supp.rating or 0.0,
            }
            if existing:
                needs_update = any(str(existing[f]) != str(attrs[f]) for f in attrs)
                if needs_update:
                    existing.write({'valid_to': fields.Datetime.now(), 'is_current': False})
                    max_key = DimSupplier.search([], order='surrogate_key desc', limit=1)
                    next_key = (max_key.surrogate_key or 0) + 1
                    DimSupplier.create({
                        'surrogate_key': next_key,
                        'source_id': supp.id,
                        'active': True,
                        'valid_from': fields.Datetime.now(),
                        'valid_to': False,
                        'is_current': True,
                        **attrs,
                    })
                    changed += 1
            else:
                max_key = DimSupplier.search([], order='surrogate_key desc', limit=1)
                next_key = (max_key.surrogate_key or 0) + 1
                DimSupplier.create({
                    'surrogate_key': next_key,
                    'source_id': supp.id,
                    'active': True,
                    'valid_from': fields.Datetime.now(),
                    'valid_to': False,
                    'is_current': True,
                    **attrs,
                })
                changed += 1
        return changed

    @api.model
    def load_dimensions(self):
        loaded = 0
        loaded += self._load_dim_date()
        loaded += self._load_dim_company()
        loaded += self._load_dim_user()
        loaded += self._load_dim_resource()
        _logger.info('ETL load dimensions: %d records loaded', loaded)
        return loaded

    @api.model
    def _load_dim_date(self):
        count = self.env['tapis.dw.dim_date'].sudo().generate_date_dimension(10)
        return count

    @api.model
    def _load_dim_company(self):
        DimCompany = self.env['tapis.dw.dim_company'].sudo()
        Company = self.env['res.company'].sudo()
        loaded = 0
        for comp in Company.search([]):
            existing = DimCompany.search([('source_id', '=', comp.id)], limit=1)
            if not existing:
                max_key = DimCompany.search([], order='surrogate_key desc', limit=1)
                next_key = (max_key.surrogate_key or 0) + 1
                DimCompany.create({
                    'surrogate_key': next_key,
                    'source_id': comp.id,
                    'active': True,
                    'name': comp.name,
                    'legal_name': comp.name,
                    'tax_id': comp.company_registry or '',
                    'currency': comp.currency_id.name if comp.currency_id else 'MAD',
                    'country': comp.country_id.name if comp.country_id else '',
                })
                loaded += 1
        return loaded

    @api.model
    def _load_dim_user(self):
        DimUser = self.env['tapis.dw.dim_user'].sudo()
        User = self.env['res.users'].sudo()
        loaded = 0
        for user in User.search([]):
            existing = DimUser.search([('source_id', '=', user.id)], limit=1)
            if not existing:
                max_key = DimUser.search([], order='surrogate_key desc', limit=1)
                next_key = (max_key.surrogate_key or 0) + 1
                role = 'Administrator' if user._is_admin() else 'User'
                DimUser.create({
                    'surrogate_key': next_key,
                    'source_id': user.id,
                    'active': True,
                    'name': user.name,
                    'login': user.login,
                    'email': user.email or '',
                    'role': role,
                })
                loaded += 1
        return loaded

    @api.model
    def _load_dim_resource(self):
        DimResource = self.env['tapis.dw.dim_resource'].sudo()
        Resource = self.env['tapis.production.resource'].sudo()
        loaded = 0
        for res in Resource.search([]):
            existing = DimResource.search([('source_id', '=', res.id)], limit=1)
            if not existing:
                max_key = DimResource.search([], order='surrogate_key desc', limit=1)
                next_key = (max_key.surrogate_key or 0) + 1
                DimResource.create({
                    'surrogate_key': next_key,
                    'source_id': res.id,
                    'active': True,
                    'name': res.name,
                    'resource_type': res.resource_type or '',
                    'capacity': res.capacity or 0.0,
                    'cost_per_hour': res.cost_per_hour or 0.0,
                    'location': res.location or '',
                })
                loaded += 1
        return loaded

    @api.model
    def load_facts(self):
        loaded = 0
        loaded += self._load_fact_sales()
        loaded += self._load_fact_inventory()
        loaded += self._load_fact_production()
        loaded += self._load_fact_finance()
        loaded += self._load_fact_quality()
        loaded += self._load_fact_support()
        self._load_inventory_snapshot()
        self._load_kpi_snapshot()
        _logger.info('ETL load facts: %d records loaded', loaded)
        return loaded

    @api.model
    def _get_date_key(self, dt):
        if not dt:
            today = fields.Date.today()
            return int(today.strftime('%Y%m%d'))
        if isinstance(dt, str):
            from odoo.tools import parse_date
            dt = parse_date(dt)
        return int(dt.strftime('%Y%m%d'))

    @api.model
    def _get_product_key(self, source_id):
        if not source_id:
            return False
        dim = self.env['tapis.dw.dim_product'].sudo().search(
            [('source_id', '=', source_id), ('is_current', '=', True)], limit=1)
        return dim.surrogate_key if dim else False

    @api.model
    def _get_customer_key(self, source_id):
        if not source_id:
            return False
        dim = self.env['tapis.dw.dim_customer'].sudo().search(
            [('source_id', '=', source_id), ('is_current', '=', True)], limit=1)
        return dim.surrogate_key if dim else False

    @api.model
    def _get_company_key(self, source_id):
        if not source_id:
            return False
        dim = self.env['tapis.dw.dim_company'].sudo().search(
            [('source_id', '=', source_id)], limit=1)
        return dim.surrogate_key if dim else False

    @api.model
    def _get_resource_key(self, source_id):
        if not source_id:
            return False
        dim = self.env['tapis.dw.dim_resource'].sudo().search(
            [('source_id', '=', source_id)], limit=1)
        return dim.surrogate_key if dim else False

    @api.model
    def _load_fact_sales(self):
        FactSales = self.env['tapis.dw.fact_sales'].sudo()
        Sale = self.env['tapis.sale'].sudo()
        last_run = self._get_last_etl_time()

        domain = [('state', 'in', ('done', 'confirmed'))]
        if last_run:
            domain += [('write_date', '>', last_run)]

        sales = Sale.search(domain)
        existing_source_ids = set(
            f[0] for f in FactSales.search([('source_id', 'in', sales.ids)]).read(['source_id'])
        ) if sales else set()

        batch = []
        for sale in sales:
            if sale.id in existing_source_ids:
                continue
            revenue = sale.total_price or 0.0
            cost = (sale.quantity or 0) * (sale.unit_price or 0) * 0.6
            gross_profit = revenue - cost
            margin = (gross_profit / revenue * 100) if revenue else 0.0

            batch.append({
                'date_key': self._get_date_key(sale.order_date or sale.create_date),
                'product_key': self._get_product_key(sale.product_id.id) if sale.product_id else False,
                'customer_key': self._get_customer_key(sale.customer_id.id) if sale.customer_id else False,
                'company_key': self._get_company_key(1),
                'quantity': sale.quantity or 0.0,
                'unit_price': sale.unit_price or 0.0,
                'revenue': revenue,
                'cost': cost,
                'gross_profit': gross_profit,
                'margin_percent': round(margin, 2),
                'discount_amount': 0.0,
                'source_id': sale.id,
            })
            if len(batch) >= 100:
                FactSales.create(batch)
                batch = []
        if batch:
            FactSales.create(batch)
        return len(batch) + (len(batch) > 0 if len(batch) % 100 == 0 else 0)

    @api.model
    def _load_fact_inventory(self):
        FactInventory = self.env['tapis.dw.fact_inventory'].sudo()
        Product = self.env['tapis.product'].sudo()
        last_run = self._get_last_etl_time()

        products = Product.search([])
        today_key = self._get_date_key(fields.Date.today())
        existing = FactInventory.search([('date_key', '=', today_key)])

        if existing and last_run:
            _logger.info('Inventory fact already loaded for today, skipping')
            return 0

        batch = []
        for prod in products:
            on_hand = prod.stock_qty or 0.0
            reserved = prod.reserved_qty or 0.0
            available = on_hand - reserved
            inv_value = on_hand * (prod.standard_cost or prod.price or 0.0)

            if on_hand <= 0:
                risk = 'high'
            elif on_hand < 10:
                risk = 'medium'
            elif on_hand < 50:
                risk = 'low'
            else:
                risk = 'none'

            batch.append({
                'date_key': today_key,
                'product_key': self._get_product_key(prod.id),
                'company_key': self._get_company_key(1),
                'on_hand_qty': on_hand,
                'reserved_qty': reserved,
                'available_qty': available,
                'inventory_value': inv_value,
                'reorder_point': 10.0,
                'stockout_risk': risk,
                'source_id': prod.id,
            })
            if len(batch) >= 100:
                FactInventory.create(batch)
                batch = []
        if batch:
            FactInventory.create(batch)
        return len(batch) + (len(batch) > 0 if len(batch) % 100 == 0 else 0)

    @api.model
    def _load_fact_production(self):
        FactProduction = self.env['tapis.dw.fact_production'].sudo()
        Production = self.env['tapis.production'].sudo()
        last_run = self._get_last_etl_time()

        domain = [('state', 'in', ('done', 'in_progress', 'delayed'))]
        if last_run:
            domain += [('write_date', '>', last_run)]

        productions = Production.search(domain)
        existing_source_ids = set(
            f[0] for f in FactProduction.search([('source_id', 'in', productions.ids)]).read(['source_id'])
        ) if productions else set()

        batch = []
        for prod in productions:
            if prod.id in existing_source_ids:
                continue

            planned = prod.planned_hours or 0.0
            actual = prod.actual_hours or planned
            efficiency = (planned / actual * 100) if actual else 100.0

            batch.append({
                'date_key': self._get_date_key(prod.actual_end_date or prod.actual_start_date or prod.create_date),
                'product_key': self._get_product_key(prod.product_id.id) if prod.product_id else False,
                'company_key': self._get_company_key(1),
                'resource_key': self._get_resource_key(prod.resource_id.id) if prod.resource_id else False,
                'produced_qty': prod.quantity or 0.0,
                'planned_hours': planned,
                'actual_hours': actual,
                'efficiency_percent': round(efficiency, 2),
                'delay_days': prod.delay_days or 0,
                'material_cost': prod.material_cost or 0.0,
                'labor_cost': prod.labor_cost or 0.0,
                'overhead_cost': prod.overhead_cost or 0.0,
                'source_id': prod.id,
            })
            if len(batch) >= 100:
                FactProduction.create(batch)
                batch = []
        if batch:
            FactProduction.create(batch)
        return len(batch)

    @api.model
    def _load_fact_finance(self):
        FactFinance = self.env['tapis.dw.fact_finance'].sudo()
        Invoice = self.env['tapis.invoice'].sudo()
        last_run = self._get_last_etl_time()

        domain = [('state', '=', 'posted')]
        if last_run:
            domain += [('write_date', '>', last_run)]

        invoices = Invoice.search(domain)
        existing = set(
            f[0] for f in FactFinance.search([('source_id', 'in', invoices.ids)]).read(['source_id'])
        ) if invoices else set()

        batch = []
        for inv in invoices:
            if inv.id in existing:
                continue
            revenue = inv.amount_total or 0.0
            expenses = revenue * 0.65
            gross = revenue - expenses
            net = gross * 0.85
            overdue = inv.amount_due or 0.0 if inv.due_date and inv.due_date < fields.Date.today() else 0.0

            batch.append({
                'date_key': self._get_date_key(inv.date or inv.create_date),
                'customer_key': self._get_customer_key(inv.customer_id.id) if inv.customer_id else False,
                'company_key': self._get_company_key(1),
                'revenue': revenue,
                'expenses': expenses,
                'gross_profit': gross,
                'net_profit': net,
                'outstanding_receivables': inv.amount_due or 0.0,
                'overdue_amount': overdue,
                'source_id': inv.id,
            })
            if len(batch) >= 100:
                FactFinance.create(batch)
                batch = []
        if batch:
            FactFinance.create(batch)
        return len(batch)

    @api.model
    def _load_fact_quality(self):
        FactQuality = self.env['tapis.dw.fact_quality'].sudo()
        Inspection = self.env['tapis.quality.inspection'].sudo()
        last_run = self._get_last_etl_time()

        domain = [('state', '=', 'completed')]
        if last_run:
            domain += [('write_date', '>', last_run)]

        inspections = Inspection.search(domain)
        existing = set(
            f[0] for f in FactQuality.search([('source_id', 'in', inspections.ids)]).read(['source_id'])
        ) if inspections else set()

        batch = []
        for insp in inspections:
            if insp.id in existing:
                continue
            defects = 1 if insp.result == 'failed' else 0

            batch.append({
                'date_key': self._get_date_key(insp.inspection_date or insp.create_date),
                'product_key': self._get_product_key(insp.product_id.id) if insp.product_id else False,
                'company_key': self._get_company_key(1),
                'inspections_count': 1,
                'defects_count': defects,
                'defect_rate': 100.0 if defects else 0.0,
                'quality_score': 0.0 if defects else 100.0,
                'source_id': insp.id,
            })
            if len(batch) >= 100:
                FactQuality.create(batch)
                batch = []
        if batch:
            FactQuality.create(batch)
        return len(batch)

    @api.model
    def _load_fact_support(self):
        FactSupport = self.env['tapis.dw.fact_support'].sudo()
        Ticket = self.env['tapis.support.ticket'].sudo()
        last_run = self._get_last_etl_time()

        domain = [('state', 'in', ('resolved', 'closed'))]
        if last_run:
            domain += [('write_date', '>', last_run)]

        tickets = Ticket.search(domain)
        existing = set(
            f[0] for f in FactSupport.search([('source_id', 'in', tickets.ids)]).read(['source_id'])
        ) if tickets else set()

        batch = []
        for tkt in tickets:
            if tkt.id in existing:
                continue
            resolution_hours = 0.0
            if tkt.create_date and tkt.write_date:
                delta = tkt.write_date - tkt.create_date
                resolution_hours = delta.total_seconds() / 3600.0

            batch.append({
                'date_key': self._get_date_key(tkt.create_date),
                'customer_key': self._get_customer_key(tkt.customer_id.id) if tkt.customer_id else False,
                'company_key': self._get_company_key(1),
                'tickets_count': 1,
                'resolution_hours': round(resolution_hours, 2),
                'satisfaction_score': 85.0,
                'source_id': tkt.id,
            })
            if len(batch) >= 100:
                FactSupport.create(batch)
                batch = []
        if batch:
            FactSupport.create(batch)
        return len(batch)

    @api.model
    def _load_inventory_snapshot(self):
        Snapshot = self.env['tapis.dw.snapshot_inventory'].sudo()
        Product = self.env['tapis.product'].sudo()
        today = fields.Date.today()

        existing = Snapshot.search([('snapshot_date', '=', today)], limit=1)
        if existing:
            return 0

        batch = []
        for prod in Product.search([]):
            on_hand = prod.stock_qty or 0.0
            reserved = prod.reserved_qty or 0.0
            batch.append({
                'snapshot_date': today,
                'product_id': prod.id,
                'on_hand_qty': on_hand,
                'reserved_qty': reserved,
                'available_qty': on_hand - reserved,
                'inventory_value': on_hand * (prod.standard_cost or prod.price or 0.0),
            })
            if len(batch) >= 100:
                Snapshot.create(batch)
                batch = []
        if batch:
            Snapshot.create(batch)
        return len(batch)

    @api.model
    def _load_kpi_snapshot(self):
        Snapshot = self.env['tapis.dw.snapshot_kpi'].sudo()
        today = fields.Date.today()

        existing = Snapshot.search([('snapshot_date', '=', today)], limit=1)
        if existing:
            return 0

        Sale = self.env['tapis.sale'].sudo()
        Production = self.env['tapis.production'].sudo()
        Invoice = self.env['tapis.invoice'].sudo()
        Customer = self.env['tapis.customer'].sudo()
        Ticket = self.env['tapis.support.ticket'].sudo()
        Product = self.env['tapis.product'].sudo()

        now = fields.Datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0)

        sales = Sale.search([('state', '=', 'done')])
        total_sales = sum(s.total_price or 0.0 for s in sales)
        monthly_sales = sum(
            s.total_price or 0.0 for s in sales
            if s.order_date and s.order_date >= month_start
        )

        total_done = Production.search_count([('state', '=', 'done')])
        total_delayed = Production.search_count([('state', '=', 'delayed')])
        total_completed = total_done + total_delayed
        on_time_rate = round(total_done / total_completed * 100, 2) if total_completed else 100.0

        Snapshot.create({
            'snapshot_date': today,
            'total_sales': total_sales,
            'monthly_sales': monthly_sales,
            'open_quotes': Sale.search_count([('state', '=', 'quotation')]),
            'overdue_invoices': Invoice.search_count([
                ('state', '=', 'posted'),
                ('due_date', '<', now),
                ('amount_due', '>', 0),
            ]),
            'active_productions': Production.search_count([('state', 'in', ('planned', 'in_progress'))]),
            'delayed_productions': total_delayed,
            'on_time_delivery_rate': on_time_rate,
            'inventory_value': sum(
                (p.stock_qty or 0) * (p.standard_cost or p.price or 0)
                for p in Product.search([])
            ),
            'low_stock_products': Product.search_count([('stock_qty', '<', 10)]),
            'gross_profit': total_sales * 0.35,
            'net_profit': total_sales * 0.20,
            'active_customers': Customer.search_count([('active', '=', True)]),
            'open_tickets': Ticket.search_count([('state', 'not in', ('closed', 'cancelled'))]),
        })
        return 1

    @api.model
    def get_sales_cube(self):
        FactSales = self.env['tapis.dw.fact_sales'].sudo()
        DimProduct = self.env['tapis.dw.dim_product'].sudo()
        DimCustomer = self.env['tapis.dw.dim_customer'].sudo()
        DimDate = self.env['tapis.dw.dim_date'].sudo()

        facts = FactSales.search([])
        if not facts:
            return {'labels': [], 'datasets': []}

        by_month = defaultdict(lambda: {'revenue': 0.0, 'cost': 0.0, 'profit': 0.0, 'count': 0})
        for f in facts:
            if f.date_key:
                dim = DimDate.search([('date_key', '=', f.date_key)], limit=1)
                if dim:
                    key = '%d-%02d' % (dim.year, dim.month)
                    by_month[key]['revenue'] += f.revenue
                    by_month[key]['cost'] += f.cost
                    by_month[key]['profit'] += f.gross_profit
                    by_month[key]['count'] += 1

        sorted_months = sorted(by_month.keys())
        return {
            'labels': sorted_months,
            'datasets': [
                {'label': 'Revenue', 'values': [by_month[m]['revenue'] for m in sorted_months]},
                {'label': 'Cost', 'values': [by_month[m]['cost'] for m in sorted_months]},
                {'label': 'Profit', 'values': [by_month[m]['profit'] for m in sorted_months]},
            ],
        }

    @api.model
    def get_inventory_cube(self):
        FactInventory = self.env['tapis.dw.fact_inventory'].sudo()
        facts = FactInventory.search([], limit=1000)
        total_value = sum(f.inventory_value for f in facts)
        total_on_hand = sum(f.on_hand_qty for f in facts)
        high_risk = len([f for f in facts if f.stockout_risk == 'high'])
        return {
            'total_value': total_value,
            'total_on_hand': total_on_hand,
            'high_risk_count': high_risk,
            'total_products': len(facts),
        }

    @api.model
    def get_profitability_cube(self):
        FactFinance = self.env['tapis.dw.fact_finance'].sudo()
        DimDate = self.env['tapis.dw.dim_date'].sudo()
        facts = FactFinance.search([])

        by_month = defaultdict(lambda: {'revenue': 0.0, 'expenses': 0.0, 'profit': 0.0})
        for f in facts:
            if f.date_key:
                dim = DimDate.search([('date_key', '=', f.date_key)], limit=1)
                if dim:
                    key = '%d-%02d' % (dim.year, dim.month)
                    by_month[key]['revenue'] += f.revenue
                    by_month[key]['expenses'] += f.expenses
                    by_month[key]['profit'] += f.net_profit

        sorted_months = sorted(by_month.keys())
        return {
            'labels': sorted_months,
            'datasets': [
                {'label': 'Revenue', 'values': [by_month[m]['revenue'] for m in sorted_months]},
                {'label': 'Expenses', 'values': [by_month[m]['expenses'] for m in sorted_months]},
                {'label': 'Net Profit', 'values': [by_month[m]['profit'] for m in sorted_months]},
            ],
        }

    @api.model
    def get_production_cube(self):
        FactProduction = self.env['tapis.dw.fact_production'].sudo()
        DimDate = self.env['tapis.dw.dim_date'].sudo()
        facts = FactProduction.search([])

        by_resource = defaultdict(lambda: {'qty': 0.0, 'hours': 0.0, 'efficiency': 0.0, 'count': 0})
        for f in facts:
            if f.resource_key:
                key = str(f.resource_key)
                by_resource[key]['qty'] += f.produced_qty
                by_resource[key]['hours'] += f.actual_hours
                by_resource[key]['efficiency'] += f.efficiency_percent
                by_resource[key]['count'] += 1

        avg_efficiency = sum(
            v['efficiency'] / v['count'] for v in by_resource.values()
        ) / len(by_resource) if by_resource else 0.0

        return {
            'total_produced': sum(f.produced_qty for f in facts),
            'total_hours': sum(f.actual_hours for f in facts),
            'avg_efficiency': round(avg_efficiency, 2),
            'total_delay_days': sum(f.delay_days for f in facts),
            'resource_count': len(by_resource),
        }

    @api.model
    def export_csv(self, model_name, stream):
        Model = self.env[model_name].sudo()
        records = Model.search([])
        if not records:
            return ''

        fields_to_export = list(records._fields.keys())
        field_names = [f for f in fields_to_export if not f.startswith('_')]
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(field_names)
        for rec in records:
            row = []
            for f in field_names:
                val = getattr(rec, f, '')
                if isinstance(val, models.BaseModel):
                    val = val.id if val else ''
                elif isinstance(val, datetime):
                    val = val.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(val, date):
                    val = val.strftime('%Y-%m-%d')
                row.append(val)
            writer.writerow(row)
        return output.getvalue()

    @api.model
    def export_excel_data(self, model_name):
        import base64
        try:
            import xlwt
        except ImportError:
            raise UserError(_('xlwt library is required for Excel export. Install with: pip install xlwt'))

        Model = self.env[model_name].sudo()
        records = Model.search([])
        workbook = xlwt.Workbook()
        sheet = workbook.add_sheet(model_name.split('.')[-1][:31])

        fields_to_export = list(records._fields.keys())
        field_names = [f for f in fields_to_export if not f.startswith('_')]
        for col, fname in enumerate(field_names):
            sheet.write(0, col, fname)
        for row, rec in enumerate(records, 1):
            for col, fname in enumerate(field_names):
                val = getattr(rec, fname, '')
                if isinstance(val, models.BaseModel):
                    val = val.id if val else ''
                elif isinstance(val, datetime):
                    val = val.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(val, date):
                    val = val.strftime('%Y-%m-%d')
                sheet.write(row, col, val)

        output = io.BytesIO()
        workbook.save(output)
        return base64.b64encode(output.getvalue())
