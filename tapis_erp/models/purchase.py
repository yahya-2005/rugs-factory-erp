from odoo import _, models, fields, api
from odoo.exceptions import UserError
from datetime import timedelta


class TapisPurchase(models.Model):
    _name = 'tapis.purchase'
    _description = 'Purchase Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.approval.mixin', 'tapis.communication.mixin', 'tapis.audit.mixin', 'tapis.signature.mixin']

    name = fields.Char(
        string='Purchase Reference',
        required=True,
        tracking=True
    )

    supplier_id = fields.Many2one(
        'tapis.supplier',
        string='Supplier',
        required=True,
        tracking=True
    )

    product_id = fields.Many2one(
        'tapis.product',
        string='Product',
        required=True,
        tracking=True
    )

    warehouse_id = fields.Many2one(
        'tapis.warehouse',
        string='Destination Warehouse',
        required=True,
        tracking=True
    )

    quantity = fields.Integer(
        string='Quantity',
        default=1,
        tracking=True
    )

    unit_price = fields.Float(
        string='Unit Price',
        tracking=True
    )

    total_price = fields.Float(
        string='Total Price',
        compute='_compute_total_price',
        store=True
    )

    expected_date = fields.Date(string='Expected Date')

    received_date = fields.Date(
        string='Received Date',
        readonly=True
    )

    delivery_delay_days = fields.Integer(
        string='Delivery Delay (Days)',
        compute='_compute_delivery_delay',
        store=True
    )

    pricelist_price = fields.Float(
        string='Pricelist Price',
        readonly=True
    )

    price_variance = fields.Float(
        string='Price Variance',
        compute='_compute_price_variance',
        store=True
    )

    approval_threshold = fields.Float(
        string='Approval Threshold',
        default=5000.0,
        company_dependent=True
    )

    note = fields.Text(string='Note')
    document_count = fields.Integer(compute='_compute_document_count')
    approval_count = fields.Integer(compute='_compute_approval_count')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = (rec.quantity or 0) * (rec.unit_price or 0.0)

    @api.depends('received_date', 'expected_date')
    def _compute_delivery_delay(self):
        for rec in self:
            if rec.received_date and rec.expected_date:
                delta = rec.received_date - rec.expected_date
                rec.delivery_delay_days = delta.days
            else:
                rec.delivery_delay_days = 0

    @api.depends('unit_price', 'pricelist_price')
    def _compute_price_variance(self):
        for rec in self:
            if rec.pricelist_price and rec.unit_price:
                rec.price_variance = rec.unit_price - rec.pricelist_price
            else:
                rec.price_variance = 0.0

    @api.onchange('supplier_id', 'product_id', 'quantity')
    def _onchange_suggest_price(self):
        if not self.supplier_id or not self.product_id:
            return
        Pricelist = self.env['tapis.supplier.pricelist']
        domain = [
            ('supplier_id', '=', self.supplier_id.id),
            ('product_id', '=', self.product_id.id),
            ('min_quantity', '<=', self.quantity or 1),
            ('active', '=', True),
        ]
        pricelist = Pricelist.search(domain, order='min_quantity desc, price asc', limit=1)
        if pricelist:
            self.unit_price = pricelist.price
            self.pricelist_price = pricelist.price
            if not self.expected_date:
                self.expected_date = fields.Date.today() + timedelta(days=pricelist.lead_time_days or 1)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only draft purchase orders can be confirmed.'))
            threshold = rec.approval_threshold or 5000.0
            if rec.total_price > threshold:
                rec.state = 'pending_approval'
                rec.message_post(body=_("Purchase order submitted for approval (total exceeds threshold of %s).") % threshold)
                rec._trigger_communication('PURCHASE_PENDING_APPROVAL')
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Pending Approval'),
                    note=_('Purchase order %s exceeds the approval threshold and requires approval.') % rec.name,
                    user_id=self.env.user.id
                )
            else:
                rec.state = 'approved'
                rec.message_post(body=_("Purchase order approved."))
                template = self.env.ref('tapis_erp.email_template_purchase_created', False)
                if template:
                    template.send_mail(rec.id, force_send=True)

    def action_approve(self):
        for rec in self:
            if rec.state != 'pending_approval':
                raise UserError(_('Only pending approval purchase orders can be approved.'))
            rec.state = 'approved'
            rec.message_post(body=_("Purchase order approved by %s.") % self.env.user.name)
            rec._trigger_communication('PURCHASE_APPROVED')
            template = self.env.ref('tapis_erp.email_template_purchase_created', False)
            if template:
                template.send_mail(rec.id, force_send=True)

    def action_reject(self):
        for rec in self:
            if rec.state != 'pending_approval':
                raise UserError(_('Only pending approval purchase orders can be rejected.'))
            rec.state = 'draft'
            rec.message_post(body=_("Purchase order rejected and returned to draft."))

    def action_receive(self):
        Quant = self.env['tapis.stock.quant']
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Only approved purchase orders can be received.'))

            quant = Quant.search([
                ('product_id', '=', rec.product_id.id),
                ('warehouse_id', '=', rec.warehouse_id.id)
            ], limit=1)

            if quant:
                quant.quantity += rec.quantity
            else:
                Quant.create({
                    'product_id': rec.product_id.id,
                    'warehouse_id': rec.warehouse_id.id,
                    'quantity': rec.quantity,
                })

            self.env['tapis.stock.move'].create({
                'name': f'PUR-{rec.name}',
                'product_id': rec.product_id.id,
                'quantity': rec.quantity,
                'move_type': 'in',
                'destination_warehouse_id': rec.warehouse_id.id,
                'note': 'Purchase received'
            })

            rec.received_date = fields.Date.today()
            rec.state = 'received'
            rec.message_post(body=_("Purchase order received successfully."))
            rec.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Purchase Received'),
                note=_('Purchase order has been received.'),
                user_id=self.env.user.id
            )

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'pending_approval', 'approved'):
                raise UserError(_('Only draft, pending approval, or approved purchase orders can be cancelled.'))
            rec.state = 'cancelled'
            rec.message_post(body=_("Purchase order cancelled."))

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('purchase_id', '=', rec.id)])

    def _compute_approval_count(self):
        for rec in self:
            rec.approval_count = self.env['tapis.approval.request'].search_count([
                ('reference_model', '=', 'tapis.purchase'), ('reference_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('purchase_id', '=', self.id)],
            'context': {'default_purchase_id': self.id},
            'target': 'current',
        }

    def _get_supplier_email(self):
        return self.supplier_id.email if self.supplier_id else False

    def _get_approval_amount(self):
        return self.total_price

    def _get_approval_category_code(self):
        return 'purchase'

    def _on_approval_approved(self):
        self.state = 'approved'
        self.message_post(body=_('Purchase order auto-approved by approval workflow.'))
        self._trigger_communication('PURCHASE_APPROVED')

    def _on_approval_rejected(self):
        self.state = 'draft'
        self.message_post(body=_('Purchase order returned to draft due to rejection.'))
