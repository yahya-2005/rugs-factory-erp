from odoo import models, fields, api, _


class TapisStockQuant(models.Model):
    _name = 'tapis.stock.quant'
    _description = 'Stock Quant'
    _inherit = ['tapis.audit.mixin']
    _rec_name = 'product_id'
    _sql_constraints = [
        ('product_warehouse_unique',
         'UNIQUE(product_id, warehouse_id)',
         'A product can only have one quant per warehouse!')
    ]

    product_id = fields.Many2one('tapis.product', string='Product', required=True)
    warehouse_id = fields.Many2one('tapis.warehouse', string='Warehouse', required=True)
    quantity = fields.Float(default=0.0)
    reserved_quantity = fields.Float(default=0.0)
    available_quantity = fields.Float(compute='_compute_available', store=True)
    inventory_value = fields.Float(compute='_compute_inventory_value', store=True)
    note = fields.Text()

    @api.depends('quantity', 'reserved_quantity')
    def _compute_available(self):
        for rec in self:
            rec.available_quantity = rec.quantity - rec.reserved_quantity

    @api.depends('quantity', 'product_id', 'product_id.cost')
    def _compute_inventory_value(self):
        for rec in self:
            rec.inventory_value = rec.quantity * (rec.product_id.cost or 0.0)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_product_stock_qty()
        return records

    def write(self, vals):
        products = self.mapped('product_id')
        result = super().write(vals)
        if 'quantity' in vals:
            products |= self.mapped('product_id')
            self.env['tapis.stock.quant']._sync_all_product_stock_qty(products)
        return result

    def unlink(self):
        products = self.mapped('product_id')
        result = super().unlink()
        self.env['tapis.stock.quant']._sync_all_product_stock_qty(products)
        return result

    def _sync_product_stock_qty(self):
        self._sync_all_product_stock_qty(self.mapped('product_id'))

    @api.model
    def _sync_all_product_stock_qty(self, products):
        for product in products:
            total = sum(self.search([('product_id', '=', product.id)]).mapped('quantity'))
            product.stock__qy = total
            product.state = 'available' if total > 0 else 'out_of_stock'
