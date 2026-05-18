from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisReorderRule(models.Model):
    _name = 'tapis.reorder.rule'
    _description = 'Reorder Rule'
    _sql_constraints = [
        ('product_warehouse_unique',
         'UNIQUE(product_id, warehouse_id)',
         'A product can only have one reorder rule per warehouse!')
    ]

    name = fields.Char(required=True)
    product_id = fields.Many2one('tapis.product', string='Product', required=True)
    warehouse_id = fields.Many2one('tapis.warehouse', string='Warehouse', required=True)
    supplier_id = fields.Many2one('tapis.supplier', string='Preferred Supplier')
    min_qty = fields.Float(string='Minimum Quantity', required=True, default=5.0)
    max_qty = fields.Float(string='Maximum Quantity', required=True, default=20.0)
    qty_to_order = fields.Float(string='Quantity to Order', compute='_compute_reorder', store=True)
    current_qty = fields.Float(string='Current Quantity', compute='_compute_reorder', store=True)
    state = fields.Selection([
        ('ok', 'OK'),
        ('to_order', 'To Order')
    ], compute='_compute_reorder', store=True)
    active = fields.Boolean(default=True)
    note = fields.Text()

    @api.depends('product_id', 'warehouse_id', 'min_qty', 'max_qty')
    def _compute_reorder(self):
        Quant = self.env['tapis.stock.quant']
        for rec in self:
            quant = Quant.search([
                ('product_id', '=', rec.product_id.id),
                ('warehouse_id', '=', rec.warehouse_id.id)
            ], limit=1)
            rec.current_qty = quant.quantity if quant else 0.0
            if rec.current_qty < rec.min_qty:
                rec.qty_to_order = rec.max_qty - rec.current_qty
                rec.state = 'to_order'
            else:
                rec.qty_to_order = 0.0
                rec.state = 'ok'

    def action_create_purchase(self):
        self.ensure_one()
        if self.state != 'to_order':
            raise UserError(_('This rule does not need replenishment at the moment.'))
        if not self.supplier_id:
            raise UserError(_('Please set a preferred supplier on this reorder rule before creating a purchase order.'))
        purchase = self.env['tapis.purchase'].create({
            'supplier_id': self.supplier_id.id,
            'product_id': self.product_id.id,
            'quantity': self.qty_to_order,
            'warehouse_id': self.warehouse_id.id,
            'unit_price': self.product_id.cost or 0.0,
            'expected_date': fields.Date.today(),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Order',
            'res_model': 'tapis.purchase',
            'view_mode': 'form',
            'res_id': purchase.id,
            'target': 'current',
        }
