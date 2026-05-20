import json
import logging
from datetime import datetime, timedelta

from odoo import http, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class TapisMobileApi(http.Controller):

    def _mobile_auth(self):
        token = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return None
        device = request.env['tapis.mobile.device'].sudo().search([
            ('device_uuid', '=', token),
            ('active', '=', True),
        ], limit=1)
        return device

    def _json_response(self, data, status=200):
        return Response(
            json.dumps(data, default=str),
            status=status,
            content_type='application/json'
        )

    def _error(self, msg, status=401):
        return self._json_response({'error': msg}, status=status)

    @http.route('/api/mobile/login', type='http', auth='user', csrf=False, methods=['POST'])
    def mobile_login(self):
        data = json.loads(request.httprequest.data or '{}')
        uuid = data.get('device_uuid')
        platform = data.get('platform', 'android')
        app_version = data.get('app_version')
        push_token = data.get('push_token')
        if not uuid:
            return self._error('device_uuid is required', 400)
        device = request.env['tapis.mobile.device'].sudo().register_device(
            uuid, platform, app_version=app_version, push_token=push_token)
        return self._json_response({
            'status': 'ok',
            'device_id': device.id,
            'token': device.device_uuid,
            'user': {'id': request.env.user.id, 'name': request.env.user.name, 'email': request.env.user.login},
        })

    @http.route('/api/mobile/sync', type='http', auth='user', csrf=False, methods=['POST'])
    def mobile_sync(self):
        device = self._mobile_auth()
        if not device:
            device = request.env['tapis.mobile.device'].sudo().search([
                ('user_id', '=', request.env.user.id), ('active', '=', True)], limit=1)
        if not device:
            return self._error('No registered device. Please login first.')

        data = json.loads(request.httprequest.data or '{}')
        last_sync = device.last_sync_datetime or datetime(2000, 1, 1)
        uploaded = data.get('uploads', [])

        sync_log = request.env['tapis.mobile.sync.log'].sudo().create({
            'device_id': device.id,
            'sync_start_datetime': datetime.now(),
            'status': 'success',
            'records_uploaded': len(uploaded),
        })

        downloaded = {}
        models_to_sync = {
            'customers': ('tapis.customer', ['id', 'name', 'email', 'phone', 'city', 'write_date']),
            'products': ('tapis.product', ['id', 'name', 'code', 'price', 'write_date']),
            'sales': ('tapis.sale', ['id', 'name', 'amount_total', 'state', 'write_date']),
            'productions': ('tapis.production', ['id', 'name', 'product_id', 'qty_producing', 'state', 'write_date']),
        }
        for key, (model, fields_list) in models_to_sync.items():
            Model = request.env[model].sudo()
            records = Model.search([('write_date', '>', last_sync)])
            downloaded[key] = [{f: str(r[f]) if hasattr(r[f], 'strftime') else r[f]
                                for f in fields_list} for r in records]
            sync_log.records_downloaded += len(records)

        device.action_sync_completed()
        sync_log.write({
            'sync_end_datetime': datetime.now(),
            'duration_seconds': (datetime.now() - sync_log.sync_start_datetime).total_seconds(),
        })

        return self._json_response({
            'status': 'ok',
            'server_time': str(datetime.now()),
            'downloaded': downloaded,
        })

    @http.route('/api/mobile/dashboard', type='http', auth='user', csrf=False, methods=['GET'])
    def mobile_dashboard(self):
        kpi_data = request.env['tapis.kpi.snapshot'].sudo().get_mobile_dashboard()
        return self._json_response(kpi_data)

    @http.route('/api/mobile/customers', type='http', auth='user', csrf=False, methods=['GET'])
    def mobile_customers(self):
        offset = int(request.params.get('offset', 0))
        limit = min(int(request.params.get('limit', 50)), 200)
        customers = request.env['tapis.customer'].sudo().search([], offset=offset, limit=limit)
        data = [{'id': c.id, 'name': c.name, 'email': c.email, 'phone': c.phone, 'city': c.city} for c in customers]
        return self._json_response({'data': data, 'count': len(customers)})

    @http.route('/api/mobile/products', type='http', auth='user', csrf=False, methods=['GET'])
    def mobile_products(self):
        offset = int(request.params.get('offset', 0))
        limit = min(int(request.params.get('limit', 50)), 200)
        barcode = request.params.get('barcode')
        domain = []
        if barcode:
            domain.append(('code', '=', barcode))
        products = request.env['tapis.product'].sudo().search(domain, offset=offset, limit=limit)
        data = [{'id': p.id, 'name': p.name, 'code': p.code, 'price': p.price,
                 'qty_available': p.qty_available} for p in products]
        return self._json_response({'data': data, 'count': len(data)})

    @http.route('/api/mobile/sales', type='http', auth='user', csrf=False, methods=['GET'])
    def mobile_sales(self):
        offset = int(request.params.get('offset', 0))
        limit = min(int(request.params.get('limit', 50)), 200)
        sales = request.env['tapis.sale'].sudo().search([], offset=offset, limit=limit)
        data = [{'id': s.id, 'name': s.name, 'customer': s.customer_id.name,
                 'amount_total': s.amount_total, 'state': s.state, 'date_order': str(s.date_order)} for s in sales]
        return self._json_response({'data': data, 'count': len(data)})

    @http.route('/api/mobile/productions', type='http', auth='user', csrf=False, methods=['GET'])
    def mobile_productions(self):
        offset = int(request.params.get('offset', 0))
        limit = min(int(request.params.get('limit', 50)), 200)
        prods = request.env['tapis.production'].sudo().search([], offset=offset, limit=limit)
        data = [{'id': p.id, 'name': p.name, 'product': p.product_id.name,
                 'qty': p.qty_producing, 'state': p.state, 'date_start': str(p.date_start)} for p in prods]
        return self._json_response({'data': data, 'count': len(data)})

    @http.route('/api/mobile/stock', type='http', auth='user', csrf=False, methods=['GET'])
    def mobile_stock(self):
        offset = int(request.params.get('offset', 0))
        limit = min(int(request.params.get('limit', 50)), 200)
        quants = request.env['tapis.stock.quant'].sudo().search([], offset=offset, limit=limit)
        data = [{'id': q.id, 'product': q.product_id.name, 'warehouse': q.warehouse_id.name,
                 'quantity': q.quantity, 'reserved': q.reserved_quantity} for q in quants]
        return self._json_response({'data': data, 'count': len(data)})

    @http.route('/api/mobile/stock/adjust', type='http', auth='user', csrf=False, methods=['POST'])
    def mobile_stock_adjust(self):
        data = json.loads(request.httprequest.data or '{}')
        product_code = data.get('product_code') or data.get('barcode')
        quantity = data.get('quantity', 0)
        warehouse_id = data.get('warehouse_id')
        if not product_code:
            return self._error('product_code or barcode required', 400)
        product = request.env['tapis.product'].sudo().search([('code', '=', product_code)], limit=1)
        if not product:
            return self._error('Product not found: %s' % product_code, 404)
        domain = [('product_id', '=', product.id)]
        if warehouse_id:
            domain.append(('warehouse_id', '=', warehouse_id))
        quant = request.env['tapis.stock.quant'].sudo().search(domain, limit=1)
        if quant:
            quant.write({'quantity': quantity})
        return self._json_response({'status': 'ok', 'product': product.name, 'new_quantity': quantity})

    @http.route('/api/mobile/notifications', type='http', auth='user', csrf=False, methods=['GET'])
    def mobile_notifications(self):
        notifications = []
        Invoice = request.env['tapis.invoice'].sudo()
        overdue = Invoice.search([('state', '=', 'posted'), ('date_due', '<', datetime.now()),
                                  ('amount_residual', '>', 0)], limit=5)
        for inv in overdue:
            notifications.append({
                'type': 'overdue_invoice',
                'title': 'Overdue Invoice',
                'message': 'Invoice %s for %s is overdue' % (inv.name, inv.partner_id.name),
                'record_id': inv.id,
            })
        Production = request.env['tapis.production'].sudo()
        delayed = Production.search([('state', '=', 'delayed')], limit=5)
        for p in delayed:
            notifications.append({
                'type': 'production_delay',
                'title': 'Production Delayed',
                'message': 'Production %s is delayed' % p.name,
                'record_id': p.id,
            })
        return self._json_response({'notifications': notifications})
