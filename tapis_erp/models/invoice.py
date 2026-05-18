from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisInvoice(models.Model):
    _name = 'tapis.invoice'
    _description = 'Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.communication.mixin', 'tapis.audit.mixin']
    _rec_name = 'name'
    _order = 'invoice_date desc, id desc'
    _sql_constraints = [
        ('sale_unique',
         'UNIQUE(sale_id)',
         'An invoice already exists for this sale order!'),
    ]

    name = fields.Char(
        string='Invoice Number',
        required=True,
        readonly=True,
        tracking=True
    )

    sale_id = fields.Many2one(
        'tapis.sale',
        string='Sale Order',
        required=True,
        tracking=True
    )

    customer_id = fields.Many2one(
        'tapis.customer',
        string='Customer',
        related='sale_id.customer_id',
        store=True,
        readonly=True
    )

    invoice_date = fields.Date(
        string='Invoice Date',
        default=fields.Date.today,
        tracking=True
    )

    due_date = fields.Date(
        string='Due Date',
        tracking=True
    )

    amount_untaxed = fields.Float(
        string='Untaxed Amount',
        related='sale_id.total_price',
        store=True,
        readonly=True
    )

    tax_rate = fields.Float(
        string='Tax Rate (%)',
        default=20.0,
        tracking=True
    )

    tax_amount = fields.Float(
        string='Tax Amount',
        compute='_compute_totals',
        store=True
    )

    amount_total = fields.Float(
        string='Total',
        compute='_compute_totals',
        store=True
    )

    amount_paid = fields.Float(
        string='Amount Paid',
        compute='_compute_paid_amount',
        store=True
    )

    amount_due = fields.Float(
        string='Amount Due',
        compute='_compute_paid_amount',
        store=True
    )

    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ], string='Payment Status', compute='_compute_paid_amount', store=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='State', default='draft', tracking=True)

    note = fields.Text(string='Note')
    document_count = fields.Integer(compute='_compute_document_count')

    def _get_customer_email(self):
        return self.customer_id.email if self.customer_id else False

    @api.depends('amount_untaxed', 'tax_rate')
    def _compute_totals(self):
        for rec in self:
            rec.tax_amount = rec.amount_untaxed * rec.tax_rate / 100.0
            rec.amount_total = rec.amount_untaxed + rec.tax_amount

    @api.depends('amount_total', 'sale_id', 'sale_id.amount_paid')
    def _compute_paid_amount(self):
        for rec in self:
            rec.amount_paid = min(rec.sale_id.amount_paid, rec.amount_total) if rec.sale_id else 0.0
            rec.amount_due = rec.amount_total - rec.amount_paid
            if rec.amount_paid == 0.0:
                rec.payment_status = 'unpaid'
            elif rec.amount_paid >= rec.amount_total:
                rec.payment_status = 'paid'
            else:
                rec.payment_status = 'partial'

    def action_post(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft invoices can be posted.'))
            if not rec.due_date:
                rec.due_date = fields.Date.add(rec.invoice_date, days=30) if rec.invoice_date else fields.Date.today()
            rec.state = 'posted'
            rec.message_post(
                body=_('Invoice %s posted successfully. Total: %s MAD')
                      % (rec.name, rec.amount_total)
            )

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'posted'):
                raise UserError(_('Only draft or posted invoices can be cancelled.'))
            rec.state = 'cancelled'
            rec.message_post(
                body=_('Invoice %s cancelled.') % rec.name
            )

    def action_register_payment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Register Payment',
            'res_model': 'tapis.customer.payment',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_customer_id': self.customer_id.id,
                'default_sale_id': self.sale_id.id,
                'default_amount': self.amount_due,
                'default_payment_date': fields.Date.today(),
            },
        }

    def action_print_invoice(self):
        self.ensure_one()
        return self.env.ref('tapis_erp.action_report_invoice').report_action(self)

    def action_open_sale(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'tapis.sale',
            'view_mode': 'form',
            'res_id': self.sale_id.id,
            'target': 'current',
        }

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('invoice_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {'default_invoice_id': self.id},
            'target': 'current',
        }
