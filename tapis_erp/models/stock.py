from odoo import models, fields


class TapisStockMove(models.Model):
    _name = 'tapis.stock.move'
    _description = 'Stock Movement'
    _order = 'date desc'

    name = fields.Char(string="Reference", required=True)

    product_id = fields.Many2one(
        'tapis.product',
        string="Product",
        required=True
    )

    quantity = fields.Integer(string="Quantity")

    move_type = fields.Selection([
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Adjustment')
    ], string="Move Type")

    source_warehouse_id = fields.Many2one('tapis.warehouse', string='Source Warehouse')
    destination_warehouse_id = fields.Many2one('tapis.warehouse', string='Destination Warehouse')

    date = fields.Datetime(
        string="Date",
        default=fields.Datetime.now
    )

    note = fields.Text(string="Notes")
