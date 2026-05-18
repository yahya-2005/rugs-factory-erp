from odoo import models, fields, api


class TapisProduct(models.Model):
    _name = 'tapis.product'
    _description = 'Tapis Product'
    _inherit = ['tapis.communication.mixin', 'tapis.audit.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Product Name', required=True)
    code = fields.Char(string='Product Code', required=True)
    description = fields.Text(string='Description')
    category = fields.Selection([('traditional', 'Traditional'), ('modern', 'Modern'), ('custom', 'Custom design')], string='Category', default='traditional')
    designer_id = fields.Many2one('res.users', string='Designer')
    price = fields.Float(string='Price', required=True)
    cost = fields.Float(string='Cost', required=True)
    stock__qy = fields.Integer(string='Stock Quantity', default=0)
    stock_qty = fields.Integer(string='Stock Quantity', related='stock__qy', store=True)
    margin = fields.Float(string='Margin', compute='_compute_margin', store=True)
    state = fields.Selection([('draft', 'Draft'), ('available', 'Available'), ('out_of_stock', 'Out of Stock')], default='out_of_stock')
    active = fields.Boolean(string='Active', default=True)
    design_id = fields.Many2one('tapis.design', string='Related Design')
    image = fields.Binary(string="Product Image")
    tag_ids = fields.Many2many('tapis.tag', string='Tags')
    production_ids = fields.One2many('tapis.production', 'product_id', string='Productions')
    sale_ids = fields.One2many('tapis.sale', 'product_id', string='Sales')
    purchase_ids = fields.One2many('tapis.purchase', 'product_id', string='Purchases')
    production_count = fields.Integer(compute='_compute_counts')
    sale_count = fields.Integer(compute='_compute_counts')
    purchase_count = fields.Integer(compute='_compute_counts')

    quant_ids = fields.One2many('tapis.stock.quant', 'product_id', string='Stock Quants')
    warehouse_count = fields.Integer(compute='_compute_warehouse_data')
    total_quant_quantity = fields.Float(compute='_compute_warehouse_data')

    reorder_rule_ids = fields.One2many('tapis.reorder.rule', 'product_id', string='Reorder Rules')
    reorder_rule_count = fields.Integer(compute='_compute_counts')

    bom_ids = fields.One2many('tapis.bom', 'product_id', string='Bills of Materials')
    bom_count = fields.Integer(compute='_compute_counts')
    manufacturing_cost = fields.Float(compute='_compute_manufacturing_cost', string='Manufacturing Cost')
    document_count = fields.Integer(compute='_compute_document_count')

    @api.depends('price', 'cost')
    def _compute_margin(self):
        for rec in self:
            rec.margin = (rec.price or 0.0) - (rec.cost or 0.0)

    def _compute_counts(self):
        for rec in self:
            rec.production_count = self.env['tapis.production'].search_count([('product_id', '=', rec.id)])
            rec.sale_count = self.env['tapis.sale'].search_count([('product_id', '=', rec.id)])
            rec.purchase_count = self.env['tapis.purchase'].search_count([('product_id', '=', rec.id)])
            rec.reorder_rule_count = self.env['tapis.reorder.rule'].search_count([('product_id', '=', rec.id)])
            rec.bom_count = self.env['tapis.bom'].search_count([('product_id', '=', rec.id)])

    @api.depends('bom_ids', 'bom_ids.total_material_cost')
    def _compute_manufacturing_cost(self):
        for rec in self:
            active_bom = rec.bom_ids.filtered(lambda b: b.active)
            rec.manufacturing_cost = active_bom[0].total_material_cost if active_bom else 0.0

    def _compute_warehouse_data(self):
        quant_model = self.env['tapis.stock.quant']
        for rec in self:
            quants = quant_model.search([('product_id', '=', rec.id)])
            rec.warehouse_count = len(quants)
            rec.total_quant_quantity = sum(quants.mapped('quantity'))

    def action_view_productions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Productions',
            'res_model': 'tapis.production',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_sales(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales',
            'res_model': 'tapis.sale',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_purchases(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchases',
            'res_model': 'tapis.purchase',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_quants(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Stock by Warehouse',
            'res_model': 'tapis.stock.quant',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_reorder_rules(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reorder Rules',
            'res_model': 'tapis.reorder.rule',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_boms(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bills of Materials',
            'res_model': 'tapis.bom',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'target': 'current',
        }

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('product_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('product_id', '=', self.id)],
            'context': {'default_product_id': self.id},
            'target': 'current',
        }
