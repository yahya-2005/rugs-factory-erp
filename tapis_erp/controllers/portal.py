from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import Home


class TapisPortal(Home):

    def _get_portal_customer(self):
        user = request.env.user
        if user.partner_id and user.partner_id.customer_rank > 0:
            customer = request.env['tapis.customer'].sudo().search([
                ('email', '=', user.login)
            ], limit=1)
            return customer
        return None

    @http.route(['/my/dashboard'], type='http', auth='user', website=True)
    def portal_dashboard(self):
        customer = self._get_portal_customer()
        if not customer:
            return request.render('tapis_erp.portal_not_found')
        dashboard = request.env['tapis.portal.dashboard'].sudo().create({
            'customer_id': customer.id,
        })
        dashboard._compute_stats()
        values = {
            'customer': customer,
            'dashboard': dashboard,
        }
        return request.render('tapis_erp.portal_dashboard_template', values)

    @http.route(['/my/orders'], type='http', auth='user', website=True)
    def portal_orders(self):
        customer = self._get_portal_customer()
        if not customer:
            return request.render('tapis_erp.portal_not_found')
        orders = request.env['tapis.sale'].sudo().search([
            ('customer_id', '=', customer.id),
            ('state', 'in', ('confirmed', 'delivered')),
        ], order='order_date desc')
        return request.render('tapis_erp.portal_orders_template', {
            'customer': customer,
            'orders': orders,
        })

    @http.route(['/my/quotes'], type='http', auth='user', website=True)
    def portal_quotes(self):
        customer = self._get_portal_customer()
        if not customer:
            return request.render('tapis_erp.portal_not_found')
        quotes = request.env['tapis.sale'].sudo().search([
            ('customer_id', '=', customer.id),
            ('state', '=', 'draft'),
        ], order='order_date desc')
        return request.render('tapis_erp.portal_quotes_template', {
            'customer': customer,
            'quotes': quotes,
        })

    @http.route(['/my/quote/<int:quote_id>/accept'], type='http', auth='user', website=True)
    def portal_quote_accept(self, quote_id):
        quote = request.env['tapis.sale'].sudo().browse(quote_id)
        if quote.customer_id != self._get_portal_customer():
            return request.render('tapis_erp.portal_not_found')
        if quote.state == 'draft':
            quote.action_confirm()
            quote.message_post(body=_('Quote accepted by customer via portal.'))
        return request.redirect('/my/quotes')

    @http.route(['/my/quote/<int:quote_id>/reject'], type='http', auth='user', website=True)
    def portal_quote_reject(self, quote_id):
        quote = request.env['tapis.sale'].sudo().browse(quote_id)
        if quote.customer_id != self._get_portal_customer():
            return request.render('tapis_erp.portal_not_found')
        if quote.state == 'draft':
            quote.state = 'cancelled'
            quote.message_post(body=_('Quote rejected by customer via portal.'))
        return request.redirect('/my/quotes')

    @http.route(['/my/invoices'], type='http', auth='user', website=True)
    def portal_invoices(self):
        customer = self._get_portal_customer()
        if not customer:
            return request.render('tapis_erp.portal_not_found')
        invoices = request.env['tapis.invoice'].sudo().search([
            ('customer_id', '=', customer.id),
        ], order='invoice_date desc')
        return request.render('tapis_erp.portal_invoices_template', {
            'customer': customer,
            'invoices': invoices,
        })

    @http.route(['/my/productions'], type='http', auth='user', website=True)
    def portal_productions(self):
        customer = self._get_portal_customer()
        if not customer:
            return request.render('tapis_erp.portal_not_found')
        sales = request.env['tapis.sale'].sudo().search([
            ('customer_id', '=', customer.id),
        ])
        product_ids = sales.mapped('product_id').ids
        productions = request.env['tapis.production'].sudo().search([
            ('product_id', 'in', product_ids),
        ], order='planned_start_date desc')
        return request.render('tapis_erp.portal_productions_template', {
            'customer': customer,
            'productions': productions,
        })

    @http.route(['/my/designs'], type='http', auth='user', website=True)
    def portal_designs(self):
        customer = self._get_portal_customer()
        if not customer:
            return request.render('tapis_erp.portal_not_found')
        sales = request.env['tapis.sale'].sudo().search([
            ('customer_id', '=', customer.id),
        ])
        product_ids = sales.mapped('product_id').ids
        designs = request.env['tapis.design'].sudo().search([
            ('product_id', 'in', product_ids),
        ], order='id desc')
        return request.render('tapis_erp.portal_designs_template', {
            'customer': customer,
            'designs': designs,
        })

    @http.route(['/my/documents'], type='http', auth='user', website=True)
    def portal_documents(self):
        customer = self._get_portal_customer()
        if not customer:
            return request.render('tapis_erp.portal_not_found')
        documents = request.env['tapis.document'].sudo().search([
            ('customer_id', '=', customer.id),
        ], order='id desc')
        return request.render('tapis_erp.portal_documents_template', {
            'customer': customer,
            'documents': documents,
        })

    @http.route(['/my/tickets'], type='http', auth='user', website=True)
    def portal_tickets(self):
        customer = self._get_portal_customer()
        if not customer:
            return request.render('tapis_erp.portal_not_found')
        tickets = request.env['tapis.support.ticket'].sudo().search([
            ('customer_id', '=', customer.id),
        ], order='id desc')
        return request.render('tapis_erp.portal_tickets_template', {
            'customer': customer,
            'tickets': tickets,
        })

    @http.route(['/my/tickets/new'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_ticket_new(self):
        customer = self._get_portal_customer()
        if not customer:
            return request.render('tapis_erp.portal_not_found')
        if request.httprequest.method == 'POST':
            vals = {
                'customer_id': customer.id,
                'contact_name': request.params.get('contact_name'),
                'contact_email': request.params.get('contact_email'),
                'subject': request.params.get('subject'),
                'description': request.params.get('description'),
                'category': request.params.get('category', 'sales'),
                'priority': request.params.get('priority', 'medium'),
            }
            ticket = request.env['tapis.support.ticket'].sudo().create(vals)
            return request.redirect('/my/tickets')
        return request.render('tapis_erp.portal_ticket_new_template', {
            'customer': customer,
        })
