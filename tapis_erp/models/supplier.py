from odoo import _, models, fields, api


class TapisSupplier(models.Model):
    _name = 'tapis.supplier'
    _description = 'Supplier'
    _inherit = ['tapis.audit.mixin']

    name = fields.Char(string='Supplier Name', required=True)
    contact_person = fields.Char(string='Contact Person')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    note = fields.Text(string='Note')
    active = fields.Boolean(string='Active', default=True)
    purchase_ids = fields.One2many('tapis.purchase', 'supplier_id', string='Purchase Orders')
    purchase_count = fields.Integer(compute='_compute_purchase_count')
    pricelist_ids = fields.One2many('tapis.supplier.pricelist', 'supplier_id', string='Pricelists')
    pricelist_count = fields.Integer(compute='_compute_pricelist_count')

    quality_score = fields.Float(string='Quality Score (0-100)', default=0.0, help='Manual quality rating 0-100')
    on_time_delivery_rate = fields.Float(string='On-Time Delivery Rate (%)', compute='_compute_delivery_kpi', store=True)
    overall_score = fields.Float(string='Overall Score', compute='_compute_overall_score', store=True)
    document_count = fields.Integer(compute='_compute_document_count')

    @api.depends('purchase_ids')
    def _compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.purchase_ids)

    @api.depends('pricelist_ids')
    def _compute_pricelist_count(self):
        for rec in self:
            rec.pricelist_count = len(rec.pricelist_ids)

    @api.depends('purchase_ids', 'purchase_ids.delivery_delay_days', 'purchase_ids.state')
    def _compute_delivery_kpi(self):
        for rec in self:
            received = rec.purchase_ids.filtered(lambda p: p.state == 'received')
            total = len(received)
            if total == 0:
                rec.on_time_delivery_rate = 0.0
                continue
            on_time = len(received.filtered(lambda p: p.delivery_delay_days is not None and p.delivery_delay_days <= 0))
            rec.on_time_delivery_rate = round((on_time / total) * 100, 2)

    @api.depends('quality_score', 'on_time_delivery_rate')
    def _compute_overall_score(self):
        for rec in self:
            rec.overall_score = (rec.quality_score + rec.on_time_delivery_rate) / 2.0

    def action_view_purchases(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchases',
            'res_model': 'tapis.purchase',
            'view_mode': 'tree,form',
            'domain': [('supplier_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_pricelists(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Supplier Pricelists',
            'res_model': 'tapis.supplier.pricelist',
            'view_mode': 'tree,form',
            'domain': [('supplier_id', '=', self.id)],
            'target': 'current',
        }

    def action_open_scorecard(self):
        return self.env.ref('tapis_erp.action_report_supplier_scorecard').report_action(self)

    def _compute_document_count(self):
        for rec in self:
            rec.document_count = self.env['tapis.document'].search_count([('supplier_id', '=', rec.id)])

    def action_view_documents(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'tapis.document',
            'view_mode': 'tree,form',
            'domain': [('supplier_id', '=', self.id)],
            'context': {'default_supplier_id': self.id},
            'target': 'current',
        }
