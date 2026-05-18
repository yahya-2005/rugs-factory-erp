from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisCustomerPayment(models.Model):
    _name = 'tapis.customer.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Customer Payment'
    _rec_name = 'name'
    _order = 'payment_date desc'

    name = fields.Char(required=True)
    customer_id = fields.Many2one('tapis.customer', string='Customer', required=True)
    sale_id = fields.Many2one('tapis.sale', string='Sale Order')
    payment_date = fields.Date(default=fields.Date.today)
    amount = fields.Float(required=True)
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    ], string='Payment Method')
    note = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], default='draft')

    def action_post(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft payments can be posted.'))
            if rec.sale_id:
                new_paid = rec.sale_id.amount_paid + rec.amount
                if new_paid > rec.sale_id.total_price:
                    raise UserError(_(
                        'Payment amount exceeds the total price of the sale order. '
                        'Current paid: %s, Total: %s, Payment: %s'
                    ) % (rec.sale_id.amount_paid, rec.sale_id.total_price, rec.amount))
                rec.sale_id.amount_paid = new_paid
            rec.state = 'posted'
            rec.message_post(body=_("Payment posted."))

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'posted'):
                raise UserError(_('Only draft or posted payments can be cancelled.'))
            if rec.state == 'posted' and rec.sale_id and rec.sale_id.amount_paid >= rec.amount:
                rec.sale_id.amount_paid -= rec.amount
            rec.state = 'cancelled'
            rec.message_post(body=_("Payment cancelled."))
