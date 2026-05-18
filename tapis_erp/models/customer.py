from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisCustomer(models.Model):
    _name = 'tapis.customer'
    _description = 'Customer'
    _inherit = ['tapis.audit.mixin']
    _rec_name = 'name'

    name = fields.Char(required=True)
    contact_person = fields.Char()
    phone = fields.Char()
    email = fields.Char()
    address = fields.Text()
    credit_limit = fields.Float(default=0.0)
    current_balance = fields.Float(compute='_compute_financial', store=True)
    total_sales_amount = fields.Float(compute='_compute_financial', store=True)
    total_paid_amount = fields.Float(compute='_compute_financial', store=True)
    active = fields.Boolean(default=True)
    note = fields.Text()

    sale_ids = fields.One2many('tapis.sale', 'customer_id', string='Sales')
    invoice_ids = fields.One2many('tapis.invoice', 'customer_id', string='Invoices')
    invoice_count = fields.Integer(compute='_compute_invoice_count')
    document_count = fields.Integer(compute='_compute_document_count')

    portal_enabled = fields.Boolean(string='Portal Enabled', default=False)
    portal_user_id = fields.Many2one('res.users', string='Portal User')
    portal_last_login = fields.Datetime(string='Portal Last Login')
    portal_access_token_ids = fields.One2many('tapis.portal.access.token',
        'customer_id', string='Portal Tokens')

    @api.depends('sale_ids', 'sale_ids.state', 'sale_ids.total_price', 'sale_ids.amount_paid')
    def _compute_financial(self):
        for rec in self:
            delivered = rec.sale_ids.filtered(lambda s: s.state == 'delivered')
            rec.total_sales_amount = sum(delivered.mapped('total_price'))
            rec.total_paid_amount = sum(delivered.mapped('amount_paid'))
            rec.current_balance = rec.total_sales_amount - rec.total_paid_amount

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def action_view_sales(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales',
            'res_model': 'tapis.sale',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'tapis.invoice',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'target': 'current',
        }

    def action_print_statement(self):
        self.ensure_one()
        return self.env.ref('tapis_erp.action_report_customer_statement').report_action(self)

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('customer_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
            'target': 'current',
        }

    def action_enable_portal(self):
        for rec in self:
            if not rec.email:
                raise UserError(_('Customer must have an email address to enable portal access.'))
            rec.portal_enabled = True
            token = self.env['tapis.portal.access.token'].generate_for_customer(rec)
            rec.message_post(body=_('Portal access enabled. Token: %s') % token.token)

    def action_disable_portal(self):
        for rec in self:
            rec.portal_enabled = False
            rec.portal_access_token_ids.write({'active': False})
            rec.message_post(body=_('Portal access disabled.'))

    def action_send_portal_invitation(self):
        self.ensure_one()
        if not self.portal_enabled:
            raise UserError(_('Portal access is not enabled for this customer.'))
        template = self.env.ref('tapis_erp.email_template_portal_invitation', False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=_('Portal invitation email sent to %s.') % self.email)
