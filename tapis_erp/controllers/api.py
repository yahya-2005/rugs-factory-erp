import json
import logging
from datetime import datetime

from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)
_logger.info('Loading TapisPublicApi controller...')
_logger.info('http module: %s', http.__file__)
_logger.info('http.route: %s', http.route)
import odoo.http as _odoo_http
_logger.info('tapis_erp controllers in registry: %d', len(_odoo_http.controllers_per_module.get('tapis_erp', [])))


class TapisPublicApi(http.Controller):

    @http.route('/tapis/api/ping', type='http', auth='public', csrf=False, methods=['GET'])
    def ping(self):
        _logger.info('PING route called!')
        return self._json_response({'status': 'ok', 'message': 'Tapis API is running'})

    def _authenticate(self):
        api_key = request.httprequest.headers.get('X-API-Key') or ''
        bearer = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')
        token = bearer or api_key
        if not token:
            raise AccessDenied(_('Missing API credentials'))
        conn = request.env['tapis.api.connection'].sudo().search([
            ('active', '=', True),
            '|',
            ('api_key', '=', token),
            ('access_token', '=', token),
        ], limit=1)
        if not conn:
            raise AccessDenied(_('Invalid API credentials'))
        return conn

    def _json_response(self, data, status=200):
        return request.make_json_response(data, status=status)

    def _error(self, msg, status=400):
        return self._json_response({'error': msg}, status=status)

    def _get_pager_params(self):
        params = request.params
        offset = int(params.get('offset', 0))
        limit = int(params.get('limit', 80))
        return offset, min(limit, 200)

    # ---- Customers ----
    @http.route('/api/v1/customers', type='http', auth='public', csrf=False, methods=['GET'])
    def customer_list(self):
        self._authenticate()
        offset, limit = self._get_pager_params()
        domain = [('active', '=', True)]
        total = request.env['tapis.customer'].sudo().search_count(domain)
        customers = request.env['tapis.customer'].sudo().search(domain, offset=offset, limit=limit)
        data = [{'id': c.id, 'name': c.name, 'email': c.email, 'phone': c.phone, 'city': c.city} for c in customers]
        return self._json_response({'count': total, 'data': data})

    @http.route('/api/v1/customers/<int:customer_id>', type='http', auth='public', csrf=False, methods=['GET'])
    def customer_get(self, customer_id):
        self._authenticate()
        cust = request.env['tapis.customer'].sudo().browse(customer_id)
        if not cust.exists():
            return self._error('Customer not found', 404)
        data = {'id': cust.id, 'name': cust.name, 'email': cust.email, 'phone': cust.phone, 'city': cust.city,
                'state': cust.state, 'country': cust.country}
        return self._json_response(data)

    @http.route('/api/v1/customers', type='http', auth='public', csrf=False, methods=['POST'])
    def customer_create(self):
        self._authenticate()
        data = json.loads(request.httprequest.data or '{}')
        vals = {k: data[k] for k in ('name', 'email', 'phone', 'city', 'state', 'country') if k in data}
        if not vals.get('name'):
            return self._error('Name is required')
        cust = request.env['tapis.customer'].sudo().create(vals)
        return self._json_response({'id': cust.id, 'message': 'Customer created'}, 201)

    @http.route('/api/v1/customers/<int:customer_id>', type='http', auth='public', csrf=False, methods=['PUT'])
    def customer_update(self, customer_id):
        self._authenticate()
        cust = request.env['tapis.customer'].sudo().browse(customer_id)
        if not cust.exists():
            return self._error('Customer not found', 404)
        data = json.loads(request.httprequest.data or '{}')
        vals = {k: data[k] for k in ('name', 'email', 'phone', 'city', 'state', 'country') if k in data}
        cust.write(vals)
        return self._json_response({'message': 'Customer updated'})

    # ---- Products ----
    @http.route('/api/v1/products', type='http', auth='public', csrf=False, methods=['GET'])
    def product_list(self):
        self._authenticate()
        offset, limit = self._get_pager_params()
        products = request.env['tapis.product'].sudo().search([], offset=offset, limit=limit)
        data = [{'id': p.id, 'name': p.name, 'code': p.code, 'category': p.category,
                 'price': p.price, 'active': p.active} for p in products]
        return self._json_response({'data': data})

    @http.route('/api/v1/products', type='http', auth='public', csrf=False, methods=['POST'])
    def product_create(self):
        self._authenticate()
        data = json.loads(request.httprequest.data or '{}')
        vals = {k: data[k] for k in ('name', 'code', 'category', 'price', 'description') if k in data}
        if not vals.get('name'):
            return self._error('Name is required')
        prod = request.env['tapis.product'].sudo().create(vals)
        return self._json_response({'id': prod.id, 'message': 'Product created'}, 201)

    # ---- Sales Orders ----
    @http.route('/api/v1/sales', type='http', auth='public', csrf=False, methods=['GET'])
    def sale_list(self):
        self._authenticate()
        offset, limit = self._get_pager_params()
        domain = [('active', '=', True)]
        sales = request.env['tapis.sale'].sudo().search(domain, offset=offset, limit=limit)
        data = [{'id': s.id, 'name': s.name, 'customer': s.customer_id.name, 'state': s.state,
                 'amount_total': s.amount_total, 'date_order': str(s.date_order)} for s in sales]
        return self._json_response({'data': data})

    # ---- Productions ----
    @http.route('/api/v1/productions', type='http', auth='public', csrf=False, methods=['GET'])
    def production_list(self):
        self._authenticate()
        offset, limit = self._get_pager_params()
        prods = request.env['tapis.production'].sudo().search([], offset=offset, limit=limit)
        data = [{'id': p.id, 'name': p.name, 'product': p.product_id.name, 'state': p.state,
                 'qty': p.qty_producing, 'date_start': str(p.date_start)} for p in prods]
        return self._json_response({'data': data})

    # ---- Inventory ----
    @http.route('/api/v1/inventory', type='http', auth='public', csrf=False, methods=['GET'])
    def inventory_list(self):
        self._authenticate()
        offset, limit = self._get_pager_params()
        quants = request.env['tapis.stock.quant'].sudo().search([], offset=offset, limit=limit)
        data = [{'id': q.id, 'product': q.product_id.name, 'warehouse': q.warehouse_id.name,
                 'quantity': q.quantity, 'reserved': q.reserved_quantity} for q in quants]
        return self._json_response({'data': data})

# Debug: check routing attributes at module load
_logger.info('Controller routes:')
for attr in dir(TapisPublicApi):
    if not attr.startswith('_'):
        fn = getattr(TapisPublicApi, attr, None)
        if fn:
            has_routing = hasattr(fn, 'routing')
            _logger.info('  %s: routing=%s', attr, has_routing)
            if has_routing:
                _logger.info('    routing=%s', fn.routing)
