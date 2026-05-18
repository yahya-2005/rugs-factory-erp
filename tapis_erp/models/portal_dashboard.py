from odoo import _, models, fields, api


class TapisPortalDashboard(models.Model):
    _name = 'tapis.portal.dashboard'
    _description = 'Portal Dashboard'
    _rec_name = 'customer_id'

    customer_id = fields.Many2one('tapis.customer', string='Customer', required=True)

    total_orders = fields.Integer(compute='_compute_stats', string='Total Orders')
    total_quotes = fields.Integer(compute='_compute_stats', string='Total Quotes')
    total_invoices = fields.Integer(compute='_compute_stats', string='Total Invoices')
    total_payments = fields.Integer(compute='_compute_stats', string='Total Payments')
    total_projects = fields.Integer(compute='_compute_stats', string='Total Projects')
    active_productions = fields.Integer(compute='_compute_stats', string='Active Productions')
    overdue_invoices = fields.Integer(compute='_compute_stats', string='Overdue Invoices')
    open_tickets = fields.Integer(compute='_compute_stats', string='Open Tickets')
    total_revenue = fields.Float(compute='_compute_stats', string='Total Revenue')

    @api.depends('customer_id')
    def _compute_stats(self):
        for rec in self:
            customer = rec.customer_id
            rec.total_orders = self.env['tapis.sale'].search_count([
                ('customer_id', '=', customer.id), ('state', '=', 'delivered')])
            rec.total_quotes = self.env['tapis.sale'].search_count([
                ('customer_id', '=', customer.id), ('state', '=', 'draft')])
            rec.total_invoices = self.env['tapis.invoice'].search_count([
                ('customer_id', '=', customer.id)])
            rec.total_payments = self.env['tapis.customer.payment'].search_count([
                ('customer_id', '=', customer.id), ('state', '=', 'paid')])
            rec.total_projects = self.env['tapis.project'].search_count([
                ('customer_id', '=', customer.id)])
            rec.active_productions = self.env['tapis.production'].search_count([
                ('state', 'in', ('planned', 'in_progress'))])
            rec.overdue_invoices = self.env['tapis.invoice'].search_count([
                ('customer_id', '=', customer.id),
                ('due_date', '<', fields.Date.today()),
                ('payment_status', '!=', 'paid')])
            rec.open_tickets = self.env['tapis.support.ticket'].search_count([
                ('customer_id', '=', customer.id),
                ('state', 'not in', ('resolved', 'closed'))])
            delivered = self.env['tapis.sale'].search([
                ('customer_id', '=', customer.id),
                ('state', '=', 'delivered')])
            rec.total_revenue = sum(delivered.mapped('total_price'))
