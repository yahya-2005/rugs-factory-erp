from odoo import _, models, fields, api, exceptions


class TapisSupplierPricelist(models.Model):
    _name = 'tapis.supplier.pricelist'
    _description = 'Supplier Pricelist'
    _rec_name = 'display_name'

    supplier_id = fields.Many2one('tapis.supplier', string='Supplier', required=True)
    product_id = fields.Many2one('tapis.product', string='Product')
    raw_material_id = fields.Many2one('tapis.raw.material', string='Raw Material')
    price = fields.Float(string='Price', required=True)
    currency = fields.Char(string='Currency', default='MAD')
    min_quantity = fields.Integer(string='Min Quantity', default=1)
    lead_time_days = fields.Integer(string='Lead Time (Days)', default=1)
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('supplier_id', 'product_id', 'raw_material_id', 'price')
    def _compute_display_name(self):
        for rec in self:
            parts = [rec.supplier_id.name or '']
            if rec.product_id:
                parts.append(rec.product_id.name)
            elif rec.raw_material_id:
                parts.append(rec.raw_material_id.name)
            parts.append(f'{rec.price:,.2f}')
            rec.display_name = ' - '.join(parts)

    _sql_constraints = [
        (
            'check_product_or_raw_material',
            "CHECK(product_id IS NOT NULL OR raw_material_id IS NOT NULL)",
            "At least one of Product or Raw Material must be set."
        ),
        (
            'check_product_raw_material_distinct',
            "CHECK(NOT (product_id IS NOT NULL AND raw_material_id IS NOT NULL))",
            "A pricelist item cannot have both a Product and a Raw Material."
        ),
        (
            'supplier_product_min_qty_unique',
            "UNIQUE(supplier_id, product_id, raw_material_id, min_quantity)",
            "A pricelist item for this supplier, product/raw material, and min quantity already exists."
        ),
    ]

    @api.constrains('min_quantity')
    def _check_min_quantity(self):
        for rec in self:
            if rec.min_quantity < 1:
                raise exceptions.ValidationError(_('Min Quantity must be at least 1.'))

    @api.constrains('price')
    def _check_price(self):
        for rec in self:
            if rec.price <= 0:
                raise exceptions.ValidationError(_('Price must be greater than zero.'))
