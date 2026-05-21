from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisSale(models.Model):
    _name = 'tapis.sale'
    _description = 'Tapis Sale'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.communication.mixin', 'tapis.audit.mixin', 'tapis.signature.mixin']

    name = fields.Char(
        string="Sale Reference",
        required=True,
        tracking=True
    )

    customer_id = fields.Many2one(
        'tapis.customer',
        string='Customer',
        required=True,
        tracking=True
    )

    customer_name = fields.Char(
        string="Customer",
        related='customer_id.name',
        store=True,
        readonly=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        tracking=True
    )

    product_id = fields.Many2one(
        'tapis.product',
        string="Product",
        required=True,
        tracking=True
    )

    warehouse_id = fields.Many2one(
        'tapis.warehouse',
        string='Source Warehouse',
        required=True,
        tracking=True
    )

    quantity = fields.Integer(
        string="Quantity",
        default=1,
        tracking=True
    )

    order_date = fields.Datetime(
        string='Order Date',
        default=fields.Datetime.now,
        tracking=True
    )

    unit_price = fields.Float(
        string='Unit Price',
        default=0.0,
        tracking=True
    )

    total_price = fields.Float(
        string="Total Price",
        compute="_compute_total_price",
        store=True
    )

    amount_paid = fields.Float(
        string='Amount Paid',
        default=0.0,
        tracking=True
    )

    balance_due = fields.Float(
        string='Balance Due',
        compute='_compute_balance_due',
        store=True
    )

    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ], compute='_compute_balance_due', store=True, tracking=True)

    cost_amount = fields.Float(
        string='Cost Amount',
        compute='_compute_profitability',
        store=True
    )

    profit_amount = fields.Float(
        string='Profit Amount',
        compute='_compute_profitability',
        store=True
    )

    margin_percent = fields.Float(
        string='Margin (%)',
        compute='_compute_profitability',
        store=True
    )

    invoice_ids = fields.One2many(
        'tapis.invoice',
        'sale_id',
        string='Invoices'
    )

    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_invoice_count'
    )
    document_count = fields.Integer(compute='_compute_document_count')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for rec in self:
            price = rec.unit_price or (rec.product_id.price if rec.product_id else 0.0)
            rec.total_price = rec.quantity * price

    @api.depends('amount_paid', 'total_price')
    def _compute_balance_due(self):
        for rec in self:
            rec.balance_due = rec.total_price - rec.amount_paid
            if rec.amount_paid == 0:
                rec.payment_status = 'unpaid'
            elif rec.amount_paid >= rec.total_price:
                rec.payment_status = 'paid'
            else:
                rec.payment_status = 'partial'

    @api.depends('quantity', 'product_id', 'total_price')
    def _compute_profitability(self):
        for rec in self:
            rec.cost_amount = rec.quantity * (rec.product_id.cost if rec.product_id else 0.0)
            rec.profit_amount = rec.total_price - rec.cost_amount
            rec.margin_percent = (rec.profit_amount / rec.total_price * 100) if rec.total_price else 0.0

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for rec in self:
            if rec.product_id:
                rec.unit_price = rec.product_id.price

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def action_create_invoice(self):
        self.ensure_one()
        if self.state != 'delivered':
            raise UserError(_('Invoice can only be created for delivered sales.'))
        if self.invoice_ids:
            raise UserError(_('An invoice already exists for this sale order.'))
        invoice = self.env['tapis.invoice'].create({
            'sale_id': self.id,
            'invoice_date': fields.Date.today(),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'tapis.invoice',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'tapis.invoice',
            'view_mode': 'tree,form',
            'domain': [('sale_id', '=', self.id)],
            'target': 'current',
        }

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('sale_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {'default_sale_id': self.id},
            'target': 'current',
        }

    def _get_customer_email(self):
        return self.customer_id.email if self.customer_id else False

    def _get_portal_url(self):
        return '/my/sales'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            template = self.env.ref('tapis_erp.email_template_quotation_created', False)
            if template:
                template.send_mail(rec.id, force_send=True)
        return records

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirmed'
            rec.message_post(body=_("Sale confirmed."))
            rec._trigger_communication('SALE_CONFIRMED')
            template = self.env.ref('tapis_erp.email_template_sale_confirmed', False)
            if template:
                template.send_mail(rec.id, force_send=True)

    def action_deliver(self):
        Quant = self.env['tapis.stock.quant']
        Inspection = self.env['tapis.quality.inspection']
        for rec in self:
            latest_inspection = Inspection.search([
                ('production_id.product_id', '=', rec.product_id.id),
                ('state', '=', 'completed'),
            ], order='inspection_date desc, id desc', limit=1)
            if latest_inspection and latest_inspection.result == 'failed':
                raise UserError(_(
                    'Delivery blocked: Product "%s" has a failed quality inspection (%s) '
                    'from %s. Please resolve the quality issues before delivering.'
                ) % (rec.product_id.name, latest_inspection.name, latest_inspection.inspection_date))
            quant = Quant.search([
                ('product_id', '=', rec.product_id.id),
                ('warehouse_id', '=', rec.warehouse_id.id)
            ], limit=1)

            total_stock = rec.product_id.stock_qty
            if total_stock < rec.quantity:
                raise UserError(_("Not enough stock!"))

            if quant and quant.quantity >= rec.quantity:
                quant.quantity -= rec.quantity
            else:
                any_quant = Quant.search([
                    ('product_id', '=', rec.product_id.id),
                    ('quantity', '>', 0),
                ], order='quantity desc', limit=1)
                if any_quant:
                    any_quant.quantity -= rec.quantity
                elif rec.product_id.stock__qy >= rec.quantity:
                    Quant.create({
                        'product_id': rec.product_id.id,
                        'warehouse_id': rec.warehouse_id.id,
                        'quantity': rec.product_id.stock__qy - rec.quantity,
                    })
                else:
                    raise UserError(_("Not enough stock in any warehouse!"))

            self.env['tapis.stock.move'].create({
                'name': f'SALE-{rec.name}',
                'product_id': rec.product_id.id,
                'quantity': rec.quantity,
                'move_type': 'out',
                'source_warehouse_id': rec.warehouse_id.id,
                'note': 'Product delivered to customer'
            })

            rec.state = 'delivered'

            rec.message_post(
                body=_("Product delivered successfully.")
            )

            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Delivery Completed'),
                note=_('Customer delivery completed.')
            )
