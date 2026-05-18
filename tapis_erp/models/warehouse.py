from odoo import models, fields, api


class TapisWarehouse(models.Model):
    _name = 'tapis.warehouse'
    _description = 'Warehouse'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    manager_id = fields.Many2one('tapis.employee', string='Manager')
    address = fields.Text()
    note = fields.Text()
    active = fields.Boolean(default=True)

    product_count = fields.Integer(compute='_compute_stats')
    total_stock_value = fields.Float(compute='_compute_stats')

    @api.depends()
    def _compute_stats(self):
        quant_model = self.env['tapis.stock.quant']
        for rec in self:
            quants = quant_model.search([('warehouse_id', '=', rec.id)])
            rec.product_count = len(quants)
            rec.total_stock_value = sum(quants.mapped('inventory_value'))

    def action_view_quants(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock Quants',
            'res_model': 'tapis.stock.quant',
            'view_mode': 'tree,form',
            'domain': [('warehouse_id', '=', self.id)],
            'target': 'current',
        }
