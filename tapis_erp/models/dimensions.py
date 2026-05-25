import logging
from datetime import datetime, date, timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class DwDimDate(models.Model):
    _name = 'tapis.dw.dim_date'
    _description = 'Date Dimension'
    _rec_name = 'full_date'
    _order = 'date_key'

    date_key = fields.Integer(string='Date Key', required=True, unique=True, index=True)
    full_date = fields.Date(string='Date', required=True)
    year = fields.Integer(string='Year')
    quarter = fields.Integer(string='Quarter')
    month = fields.Integer(string='Month')
    month_name = fields.Char(string='Month Name')
    week = fields.Integer(string='Week of Year')
    day = fields.Integer(string='Day of Month')
    day_of_week = fields.Integer(string='Day of Week')
    day_name = fields.Char(string='Day Name')
    is_weekend = fields.Boolean(string='Is Weekend')
    is_holiday = fields.Boolean(string='Is Holiday', default=False)
    fiscal_year = fields.Char(string='Fiscal Year')
    fiscal_period = fields.Char(string='Fiscal Period')

    def name_get(self):
        return [(rec.id, rec.full_date.strftime('%Y-%m-%d') if rec.full_date else str(rec.date_key)) for rec in self]

    @api.model
    def generate_date_dimension(self, years=10):
        existing = self.search_count([])
        if existing:
            _logger.info('Date dimension already has %d records, skipping generation', existing)
            return existing

        today = date.today()
        start_date = date(today.year - 1, 1, 1)
        end_date = date(today.year + years - 1, 12, 31)
        delta = end_date - start_date

        batch = []
        for i in range(delta.days + 1):
            d = start_date + timedelta(days=i)
            batch.append({
                'date_key': int(d.strftime('%Y%m%d')),
                'full_date': d,
                'year': d.year,
                'quarter': (d.month - 1) // 3 + 1,
                'month': d.month,
                'month_name': d.strftime('%B'),
                'week': d.isocalendar()[1],
                'day': d.day,
                'day_of_week': d.weekday(),
                'day_name': d.strftime('%A'),
                'is_weekend': d.weekday() >= 5,
                'fiscal_year': str(d.year),
                'fiscal_period': '%d-%02d' % (d.year, d.month),
            })
            if len(batch) >= 500:
                self.create(batch)
                batch = []
        if batch:
            self.create(batch)
        count = self.search_count([])
        _logger.info('Generated %d date dimension records', count)
        return count


class DwDimProduct(models.Model):
    _name = 'tapis.dw.dim_product'
    _description = 'Product Dimension'
    _rec_name = 'name'
    _order = 'name'

    surrogate_key = fields.Integer(string='Surrogate Key', required=True, unique=True, index=True)
    source_id = fields.Integer(string='Source ID')
    active = fields.Boolean(default=True)

    name = fields.Char(string='Product Name')
    code = fields.Char(string='Product Code')
    category = fields.Char(string='Category')
    tags = fields.Char(string='Tags')
    standard_cost = fields.Float(string='Standard Cost')
    list_price = fields.Float(string='List Price')
    uom = fields.Char(string='Unit of Measure')

    valid_from = fields.Datetime(string='Valid From')
    valid_to = fields.Datetime(string='Valid To')
    is_current = fields.Boolean(string='Is Current', default=True)

    _sql_constraints = [
        ('surrogate_key_unique', 'unique(surrogate_key)', 'Surrogate key must be unique!'),
    ]


class DwDimCustomer(models.Model):
    _name = 'tapis.dw.dim_customer'
    _description = 'Customer Dimension'
    _rec_name = 'name'
    _order = 'name'

    surrogate_key = fields.Integer(string='Surrogate Key', required=True, unique=True, index=True)
    source_id = fields.Integer(string='Source ID')
    active = fields.Boolean(default=True)

    name = fields.Char(string='Customer Name')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    address = fields.Text(string='Address')
    city = fields.Char(string='City')
    country = fields.Char(string='Country')
    segment = fields.Char(string='Segment')
    credit_limit = fields.Float(string='Credit Limit')

    valid_from = fields.Datetime(string='Valid From')
    valid_to = fields.Datetime(string='Valid To')
    is_current = fields.Boolean(string='Is Current', default=True)

    _sql_constraints = [
        ('surrogate_key_unique', 'unique(surrogate_key)', 'Surrogate key must be unique!'),
    ]


class DwDimCompany(models.Model):
    _name = 'tapis.dw.dim_company'
    _description = 'Company Dimension'
    _rec_name = 'name'
    _order = 'name'

    surrogate_key = fields.Integer(string='Surrogate Key', required=True, unique=True, index=True)
    source_id = fields.Integer(string='Source ID')
    active = fields.Boolean(default=True)

    name = fields.Char(string='Company Name')
    legal_name = fields.Char(string='Legal Name')
    tax_id = fields.Char(string='Tax ID')
    currency = fields.Char(string='Currency')
    country = fields.Char(string='Country')

    _sql_constraints = [
        ('surrogate_key_unique', 'unique(surrogate_key)', 'Surrogate key must be unique!'),
    ]


class DwDimSupplier(models.Model):
    _name = 'tapis.dw.dim_supplier'
    _description = 'Supplier Dimension'
    _rec_name = 'name'
    _order = 'name'

    surrogate_key = fields.Integer(string='Surrogate Key', required=True, unique=True, index=True)
    source_id = fields.Integer(string='Source ID')
    active = fields.Boolean(default=True)

    name = fields.Char(string='Supplier Name')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    country = fields.Char(string='Country')
    payment_terms = fields.Char(string='Payment Terms')
    rating = fields.Float(string='Rating')

    valid_from = fields.Datetime(string='Valid From')
    valid_to = fields.Datetime(string='Valid To')
    is_current = fields.Boolean(string='Is Current', default=True)

    _sql_constraints = [
        ('surrogate_key_unique', 'unique(surrogate_key)', 'Surrogate key must be unique!'),
    ]


class DwDimUser(models.Model):
    _name = 'tapis.dw.dim_user'
    _description = 'User Dimension'
    _rec_name = 'name'
    _order = 'name'

    surrogate_key = fields.Integer(string='Surrogate Key', required=True, unique=True, index=True)
    source_id = fields.Integer(string='Source ID')
    active = fields.Boolean(default=True)

    name = fields.Char(string='User Name')
    login = fields.Char(string='Login')
    email = fields.Char(string='Email')
    role = fields.Char(string='Role')
    department = fields.Char(string='Department')

    _sql_constraints = [
        ('surrogate_key_unique', 'unique(surrogate_key)', 'Surrogate key must be unique!'),
    ]


class DwDimResource(models.Model):
    _name = 'tapis.dw.dim_resource'
    _description = 'Production Resource Dimension'
    _rec_name = 'name'
    _order = 'name'

    surrogate_key = fields.Integer(string='Surrogate Key', required=True, unique=True, index=True)
    source_id = fields.Integer(string='Source ID')
    active = fields.Boolean(default=True)

    name = fields.Char(string='Resource Name')
    resource_type = fields.Char(string='Resource Type')
    capacity = fields.Float(string='Capacity')
    cost_per_hour = fields.Float(string='Cost per Hour')
    location = fields.Char(string='Location')

    _sql_constraints = [
        ('surrogate_key_unique', 'unique(surrogate_key)', 'Surrogate key must be unique!'),
    ]
