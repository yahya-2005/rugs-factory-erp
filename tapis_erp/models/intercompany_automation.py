from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'tapis.sale'

    intercompany_purchase_id = fields.Many2one('tapis.purchase', string='Intercompany Purchase',
        readonly=True, copy=False)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for sale in self:
            if sale.company_id:
                other_company = self.env['res.company'].search([
                    ('id', '!=', sale.company_id.id)
                ], limit=1)
                if other_company:
                    rule = self.env['tapis.intercompany.rule']._get_rule(
                        sale.company_id, other_company
                    )
                    if rule and rule.auto_create_purchase:
                        sale._create_intercompany_purchase(other_company, rule)
        return res

    def _create_intercompany_purchase(self, target_company, rule):
        self.ensure_one()
        supplier = self.env['tapis.supplier'].search([
            ('company_id', '=', target_company.id),
        ], limit=1)
        if not supplier:
            self.env['tapis.security.incident'].create({
                'name': _('Intercompany: No supplier found in target company'),
                'user_id': self.env.user.id,
                'model_name': 'tapis.sale',
                'operation': 'intercompany_failed',
                'description': _('No supplier record found in company %s for intercompany purchase.') % target_company.name,
                'severity': 'medium',
            })
            return False
        margin = 1 + (rule.margin_percent / 100.0) if rule.margin_percent else 1.0
        purchase = self.env['tapis.purchase'].sudo().with_context(
            force_company=target_company.id
        ).create({
            'supplier_id': supplier.id,
            'product_id': self.product_id.id,
            'quantity': self.quantity,
            'unit_price': self.unit_price * margin,
            'company_id': target_company.id,
        })
        self.intercompany_purchase_id = purchase.id
        if rule.auto_validate_documents:
            purchase.sudo().with_context(force_company=target_company.id).action_confirm()
        return True


class PurchaseOrder(models.Model):
    _inherit = 'tapis.purchase'

    intercompany_sale_id = fields.Many2one('tapis.sale', string='Intercompany Sale',
        readonly=True, copy=False)

    def action_approve(self):
        res = super(PurchaseOrder, self).action_approve()
        for purchase in self:
            if purchase.company_id:
                other_company = self.env['res.company'].search([
                    ('id', '!=', purchase.company_id.id)
                ], limit=1)
                if other_company:
                    rule = self.env['tapis.intercompany.rule']._get_rule(
                        other_company, purchase.company_id
                    )
                    if rule and rule.auto_create_sale:
                        purchase._create_intercompany_sale(other_company, rule)
        return res

    def _create_intercompany_sale(self, target_company, rule):
        self.ensure_one()
        customer = self.env['tapis.customer'].search([
            ('company_id', '=', target_company.id),
        ], limit=1)
        if not customer:
            self.env['tapis.security.incident'].create({
                'name': _('Intercompany: No customer found in target company'),
                'user_id': self.env.user.id,
                'model_name': 'tapis.purchase',
                'operation': 'intercompany_failed',
                'description': _('No customer record found in company %s for intercompany sale.') % target_company.name,
                'severity': 'medium',
            })
            return False
        margin = 1 + (rule.margin_percent / 100.0) if rule.margin_percent else 1.0
        sale = self.env['tapis.sale'].sudo().with_context(
            force_company=target_company.id
        ).create({
            'customer_id': customer.id,
            'product_id': self.product_id.id,
            'quantity': self.quantity,
            'unit_price': self.unit_price * margin,
            'company_id': target_company.id,
        })
        self.intercompany_sale_id = sale.id
        return True
