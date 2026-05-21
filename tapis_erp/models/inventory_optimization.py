from odoo import _, models, fields, api
from odoo.exceptions import UserError
import math


class TapisInventoryOptimization(models.Model):
    _name = 'tapis.inventory.optimization'
    _description = 'Inventory Optimization'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char(required=True, readonly=True, default='New')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    product_id = fields.Many2one('tapis.product', string='Product', required=True, tracking=True)
    warehouse_id = fields.Many2one('tapis.warehouse', string='Warehouse', tracking=True)

    average_daily_demand = fields.Float(string='Avg Daily Demand', tracking=True)
    demand_std_dev = fields.Float(string='Demand Std Dev', tracking=True)
    lead_time_days = fields.Float(string='Lead Time (Days)', default=1.0, tracking=True)
    service_level_percent = fields.Float(string='Service Level %', default=95.0, tracking=True)
    annual_holding_cost = fields.Float(string='Annual Holding Cost/Unit', tracking=True,
        help='Cost to hold one unit for one year (H)')
    ordering_cost = fields.Float(string='Ordering Cost', default=50.0, tracking=True,
        help='Cost per order placed (S)')

    safety_stock_qty = fields.Float(compute='_compute_formulas', store=True, string='Safety Stock')
    reorder_point_qty = fields.Float(compute='_compute_formulas', store=True, string='Reorder Point')
    eoq_qty = fields.Float(compute='_compute_formulas', store=True, string='EOQ')
    annual_demand = fields.Float(compute='_compute_formulas', store=True, string='Annual Demand')

    current_stock_qty = fields.Float(compute='_compute_stock_data', store=True, string='Current Stock')
    stock_gap_qty = fields.Float(compute='_compute_stock_data', store=True, string='Stock Gap')
    stockout_risk_percent = fields.Float(compute='_compute_stock_data', store=True, string='Stockout Risk %')
    stockout_risk_level = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], compute='_compute_stock_data', store=True, string='Stockout Risk Level')

    recommended_order_qty = fields.Float(compute='_compute_formulas', store=True, string='Recommended Order Qty')
    recommended_supplier_id = fields.Many2one('tapis.supplier', compute='_compute_recommended_supplier',
        store=True, string='Recommended Supplier')

    purchase_order_id = fields.Many2one('tapis.purchase', string='Purchase Order', readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('analyzed', 'Analyzed'),
        ('approved', 'Approved'),
        ('ordered', 'Ordered'),
    ], default='draft', tracking=True)

    recommendation_line_ids = fields.One2many('tapis.inventory.optimization.line',
        'optimization_id', string='Supplier Recommendations')
    notes = fields.Text(string='Notes')

    def _z_score(self):
        vals = {
            90.0: 1.28,
            95.0: 1.65,
            97.5: 1.96,
            99.0: 2.33,
        }
        nearest = min(vals.keys(), key=lambda k: abs(k - self.service_level_percent))
        return vals[nearest]

    @api.depends('average_daily_demand', 'demand_std_dev', 'lead_time_days',
                 'service_level_percent', 'annual_holding_cost', 'ordering_cost')
    def _compute_formulas(self):
        for rec in self:
            add = rec.average_daily_demand or 0.0
            std = rec.demand_std_dev or 0.0
            lt = rec.lead_time_days or 1.0
            sl = rec.service_level_percent or 95.0
            h = rec.annual_holding_cost or 0.0
            s = rec.ordering_cost or 50.0

            z = rec._z_score()
            rec.safety_stock_qty = z * std * math.sqrt(lt)

            rec.reorder_point_qty = add * lt + rec.safety_stock_qty

            rec.annual_demand = add * 365.0

            if h > 0 and s > 0 and rec.annual_demand > 0:
                rec.eoq_qty = math.sqrt(2.0 * rec.annual_demand * s / h)
            else:
                rec.eoq_qty = 0.0

            if rec.eoq_qty > 0:
                rec.recommended_order_qty = rec.eoq_qty
            else:
                gap = max(rec.reorder_point_qty - rec.current_stock_qty, 0.0)
                rec.recommended_order_qty = gap if gap > 0 else rec.reorder_point_qty

    @api.depends('product_id', 'warehouse_id', 'reorder_point_qty', 'safety_stock_qty')
    def _compute_stock_data(self):
        Quant = self.env['tapis.stock.quant']
        for rec in self:
            domain = [('product_id', '=', rec.product_id.id)]
            if rec.warehouse_id:
                domain.append(('warehouse_id', '=', rec.warehouse_id.id))
            quants = Quant.search(domain)
            rec.current_stock_qty = sum(quants.mapped('quantity')) if quants else 0.0

            rp = rec.reorder_point_qty or 0.0
            ss = rec.safety_stock_qty or 0.0
            cs = rec.current_stock_qty or 0.0

            rec.stock_gap_qty = cs - rp

            if rp > 0:
                ratio = cs / rp
                if ratio >= 2.0:
                    rec.stockout_risk_level = 'low'
                    rec.stockout_risk_percent = max(0.0, 100.0 - ratio * 25.0)
                elif ratio >= 1.0:
                    rec.stockout_risk_level = 'medium'
                    rec.stockout_risk_percent = max(0.0, 100.0 - ratio * 40.0)
                elif ss > 0 and cs >= ss:
                    rec.stockout_risk_level = 'high'
                    rec.stockout_risk_percent = max(0.0, 100.0 - (cs / rp) * 60.0)
                else:
                    rec.stockout_risk_level = 'critical'
                    rec.stockout_risk_percent = min(100.0, (1.0 - cs / max(rp, 1.0)) * 100.0)
            else:
                rec.stockout_risk_level = 'low'
                rec.stockout_risk_percent = 0.0

    @api.depends('product_id', 'recommendation_line_ids', 'recommendation_line_ids.total_score')
    def _compute_recommended_supplier(self):
        for rec in self:
            best = rec.recommendation_line_ids.filtered(lambda l: l.recommended)
            if best:
                rec.recommended_supplier_id = best[0].supplier_id
            else:
                top = rec.recommendation_line_ids.sorted(
                    key=lambda l: l.total_score or 0.0, reverse=True)
                rec.recommended_supplier_id = top[0].supplier_id if top else False

    def action_analyze_inventory(self):
        for rec in self:
            rec._compute_formulas()
            rec._compute_stock_data()
            rec._generate_supplier_recommendations()
            rec.state = 'analyzed'
            template = self.env.ref('tapis_erp.email_template_inventory_recommendation', False)
            if template:
                template.send_mail(rec.id, force_send=True)

    def action_approve(self):
        for rec in self:
            if rec.state != 'analyzed':
                raise UserError(_('Only analyzed optimizations can be approved.'))
            rec.state = 'approved'

    def action_create_purchase_order(self):
        self.ensure_one()
        if self.state not in ('analyzed', 'approved'):
            raise UserError(_('Optimization must be analyzed or approved before ordering.'))
        if self.purchase_order_id:
            raise UserError(_('A purchase order already exists for this optimization.'))
        if not self.recommended_supplier_id:
            raise UserError(_('No recommended supplier found.'))
        qty = self.recommended_order_qty or 0
        if qty <= 0:
            raise UserError(_('Recommended order quantity must be greater than zero.'))
        po = self.env['tapis.purchase'].create({
            'name': self.env['ir.sequence'].next_by_code('tapis.purchase') or '/',
            'supplier_id': self.recommended_supplier_id.id,
            'product_id': self.product_id.id,
            'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
            'quantity': qty,
            'state': 'draft',
            'note': _('Auto-generated from inventory optimization: %s') % self.name,
        })
        self.purchase_order_id = po.id
        self.state = 'ordered'

    def action_mark_ordered(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Only approved optimizations can be marked ordered.'))
            rec.state = 'ordered'

    def _generate_supplier_recommendations(self):
        self.ensure_one()
        Pricelist = self.env['tapis.supplier.pricelist']
        pricelists = Pricelist.search([
            ('product_id', '=', self.product_id.id),
            ('active', '=', True),
        ])
        if not pricelists:
            pricelists = Pricelist.search([
                ('product_id', '=', False),
                ('raw_material_id', '=', False),
                ('active', '=', True),
            ])
        seen = set()
        line_data = []
        for pl in pricelists:
            sid = pl.supplier_id.id
            if sid in seen:
                continue
            seen.add(sid)
            supplier = pl.supplier_id
            quality = supplier.quality_score or 50.0
            otif = supplier.on_time_delivery_rate or 50.0
            price = pl.price or 0
            lt = pl.lead_time_days or 1

            max_price = max(p.price for p in pricelists if p.price) or 1
            price_score = max(0.0, 100.0 - (price / max_price) * 100.0) if max_price else 50.0
            lt_score = max(0.0, 100.0 - (lt / max(max(lt for p in pricelists if p.lead_time_days), 1)) * 100.0)

            total = price_score * 0.3 + lt_score * 0.2 + quality * 0.25 + otif * 0.25
            line_data.append({
                'supplier_id': sid,
                'supplier_price': price,
                'lead_time_days': lt,
                'quality_score': quality,
                'on_time_delivery_rate': otif,
                'total_score': round(total, 2),
            })

        line_data.sort(key=lambda x: x['total_score'], reverse=True)
        if line_data:
            line_data[0]['recommended'] = True

        self.recommendation_line_ids.unlink()
        for seq, ld in enumerate(line_data, 1):
            self.env['tapis.inventory.optimization.line'].create({
                'optimization_id': self.id,
                'sequence': seq,
                'supplier_id': ld['supplier_id'],
                'supplier_price': ld['supplier_price'],
                'lead_time_days': ld['lead_time_days'],
                'quality_score': ld['quality_score'],
                'on_time_delivery_rate': ld['on_time_delivery_rate'],
                'total_score': ld['total_score'],
                'recommended': ld.get('recommended', False),
            })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('tapis.inventory.optimization') or 'New'
        return super().create(vals_list)


class TapisInventoryOptimizationLine(models.Model):
    _name = 'tapis.inventory.optimization.line'
    _description = 'Inventory Optimization Supplier Line'
    _order = 'sequence'

    optimization_id = fields.Many2one('tapis.inventory.optimization',
        string='Optimization', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)

    supplier_id = fields.Many2one('tapis.supplier', string='Supplier', required=True)
    supplier_price = fields.Float(string='Price')
    lead_time_days = fields.Float(string='Lead Time (Days)')
    quality_score = fields.Float(string='Quality Score')
    on_time_delivery_rate = fields.Float(string='On-Time Delivery %')
    total_score = fields.Float(string='Total Score')
    recommended = fields.Boolean(string='Recommended')
