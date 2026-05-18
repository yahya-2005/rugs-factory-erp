from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisStockTransfer(models.Model):
    _name = 'tapis.stock.transfer'
    _description = 'Internal Stock Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Transfer Reference', required=True, tracking=True, default=lambda self: self.env['ir.sequence'].next_by_code('tapis.transfer.code'))
    source_warehouse_id = fields.Many2one('tapis.warehouse', string='From Warehouse', required=True, tracking=True)
    destination_warehouse_id = fields.Many2one('tapis.warehouse', string='To Warehouse', required=True, tracking=True)
    product_id = fields.Many2one('tapis.product', string='Product', required=True, tracking=True)
    quantity = fields.Float(default=1.0, tracking=True)
    transfer_date = fields.Date()
    note = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='draft', tracking=True)

    @api.onchange('source_warehouse_id', 'destination_warehouse_id')
    def _onchange_warehouses(self):
        for rec in self:
            if rec.source_warehouse_id and rec.destination_warehouse_id and rec.source_warehouse_id == rec.destination_warehouse_id:
                return {'warning': {'title': _('Warning'), 'message': _('Source and destination warehouses must be different.')}}

    def action_confirm(self):
        for rec in self:
            if rec.source_warehouse_id == rec.destination_warehouse_id:
                raise UserError(_('Source and destination warehouses must be different.'))
            rec.state = 'confirmed'
            rec.message_post(body=_("Transfer confirmed."))

    def action_done(self):
        Quant = self.env['tapis.stock.quant']
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_('Only confirmed transfers can be completed.'))

            source_quant = Quant.search([
                ('product_id', '=', rec.product_id.id),
                ('warehouse_id', '=', rec.source_warehouse_id.id)
            ], limit=1)

            if not source_quant or source_quant.quantity < rec.quantity:
                raise UserError(_('Not enough stock in source warehouse!'))

            source_quant.quantity -= rec.quantity

            dest_quant = Quant.search([
                ('product_id', '=', rec.product_id.id),
                ('warehouse_id', '=', rec.destination_warehouse_id.id)
            ], limit=1)

            if dest_quant:
                dest_quant.quantity += rec.quantity
            else:
                Quant.create({
                    'product_id': rec.product_id.id,
                    'warehouse_id': rec.destination_warehouse_id.id,
                    'quantity': rec.quantity,
                })

            self.env['tapis.stock.move'].create({
                'name': f'TRF-{rec.name}',
                'product_id': rec.product_id.id,
                'quantity': rec.quantity,
                'move_type': 'adjustment',
                'source_warehouse_id': rec.source_warehouse_id.id,
                'destination_warehouse_id': rec.destination_warehouse_id.id,
                'note': f'Internal transfer from {rec.source_warehouse_id.name} to {rec.destination_warehouse_id.name}',
            })

            rec.transfer_date = fields.Date.today()
            rec.state = 'done'
            rec.message_post(body=_("Transfer completed successfully."))

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('draft', 'confirmed'):
                raise UserError(_('Only draft or confirmed transfers can be cancelled.'))
            rec.state = 'cancelled'
            rec.message_post(body=_("Transfer cancelled."))
