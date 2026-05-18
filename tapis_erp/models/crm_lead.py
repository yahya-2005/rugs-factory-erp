from odoo import _, models, fields, api
from odoo.exceptions import UserError


class TapisCrmLead(models.Model):
    _name = 'tapis.crm.lead'
    _description = 'CRM Lead / Opportunity'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'tapis.communication.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    def init(self):
        if not self.env['ir.sequence'].search([('code', '=', 'tapis.crm.lead.code')], limit=1):
            self.env['ir.sequence'].create({
                'name': 'CRM Lead Code',
                'code': 'tapis.crm.lead.code',
                'prefix': 'CRM/',
                'padding': 5,
                'number_next': 1,
                'number_increment': 1,
            })

    name = fields.Char(string='Opportunity Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, readonly=True, default=lambda s: _('New'))
    contact_name = fields.Char(string='Contact Name')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    company_name = fields.Char(string='Company')
    address = fields.Text(string='Address')

    customer_id = fields.Many2one('tapis.customer', string='Customer', tracking=True)
    salesperson_id = fields.Many2one('tapis.employee', string='Salesperson', tracking=True)
    stage_id = fields.Many2one(
        'tapis.crm.stage', string='Stage',
        required=True, tracking=True,
        default=lambda self: self._default_stage_id(),
    )
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='medium', tracking=True)

    color = fields.Integer(string='Color Index', default=0)

    expected_revenue = fields.Float(string='Expected Revenue', default=0.0, tracking=True)
    probability = fields.Float(string='Probability (%)', related='stage_id.probability', store=True)
    weighted_revenue = fields.Float(
        string='Weighted Revenue',
        compute='_compute_weighted_revenue', store=True,
    )
    expected_closing_date = fields.Date(string='Expected Closing')

    source = fields.Selection([
        ('website', 'Website'),
        ('phone', 'Phone Call'),
        ('email', 'Email'),
        ('referral', 'Referral'),
        ('social_media', 'Social Media'),
        ('exhibition', 'Exhibition'),
        ('other', 'Other'),
    ], string='Source', default='other')

    description = fields.Html(string='Description')
    tag_ids = fields.Many2many('tapis.project.tag', string='Tags')
    related_sale_id = fields.Many2one('tapis.sale', string='Related Sale Order')

    state = fields.Selection([
        ('open', 'Open'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], string='Status', default='open', required=True, tracking=True)

    active = fields.Boolean(string='Active', default=True)
    note = fields.Text(string='Notes')

    def action_view_opportunities(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Opportunities',
            'res_model': 'tapis.crm.lead',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', '=', self.id)],
            'target': 'current',
        }

    @api.model
    def _default_stage_id(self):
        return self.env['tapis.crm.stage'].search([], order='sequence', limit=1) or False

    @api.depends('expected_revenue', 'probability')
    def _compute_weighted_revenue(self):
        for rec in self:
            rec.weighted_revenue = rec.expected_revenue * rec.probability / 100.0

    def _get_customer_email(self):
        return self.email

    def action_mark_won(self):
        for rec in self:
            if rec.state != 'open':
                raise UserError(_('Only open opportunities can be marked as won.'))
            rec.state = 'won'
            won_stage = self.env['tapis.crm.stage'].search([('is_won', '=', True)], limit=1)
            if won_stage:
                rec.stage_id = won_stage
            rec.message_post(body=_('Opportunity marked as won.'))
            rec._trigger_communication('CRM_WON_OPPORTUNITY')

    def action_mark_lost(self):
        for rec in self:
            if rec.state != 'open':
                raise UserError(_('Only open opportunities can be marked as lost.'))
            rec.state = 'lost'
            lost_stage = self.env['tapis.crm.stage'].search([('is_lost', '=', True)], limit=1)
            if lost_stage:
                rec.stage_id = lost_stage
            rec.message_post(body=_('Opportunity marked as lost.'))

    def action_reset_open(self):
        for rec in self:
            if rec.state not in ('won', 'lost'):
                raise UserError(_('Only won or lost opportunities can be reset to open.'))
            rec.state = 'open'
            first_stage = self.env['tapis.crm.stage'].search([], order='sequence', limit=1)
            if first_stage:
                rec.stage_id = first_stage
            rec.message_post(body=_('Opportunity reset to open.'))

    def action_convert_to_customer(self):
        for rec in self:
            if rec.customer_id:
                raise UserError(_('A customer already exists for this opportunity.'))
            customer = self.env['tapis.customer'].create({
                'name': rec.company_name or rec.contact_name or rec.name,
                'phone': rec.phone or '',
                'email': rec.email or '',
                'address': rec.address or '',
            })
            rec.customer_id = customer
            rec.message_post(
                body=_('Customer "%s" created from this opportunity.') % customer.name
            )

    def action_create_sale(self):
        self.ensure_one()
        if not self.customer_id:
            self.action_convert_to_customer()
        if self.related_sale_id:
            raise UserError(_('A sale order already exists for this opportunity.'))
        product_id = self.env.context.get('default_product_id')
        if not product_id:
            raise UserError(_(
                'Please go to the product list and open the product you want to sell, '
                'then create the opportunity from the product form.'
            ))
        product = self.env['tapis.product'].browse(product_id)
        warehouse = self.env['tapis.warehouse'].search([], limit=1)
        if not warehouse:
            raise UserError(_('No warehouse configured. Please create a warehouse first.'))
        sale = self.env['tapis.sale'].create({
            'name': self.env['ir.sequence'].next_by_code('tapis.sale.code') or _('New'),
            'customer_id': self.customer_id.id,
            'product_id': product_id,
            'warehouse_id': warehouse.id,
            'quantity': 1,
            'unit_price': product.price or self.expected_revenue,
        })
        self.related_sale_id = sale
        self.message_post(
            body=_('Sale order "%s" created from this opportunity.') % sale.name
        )
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Order',
            'res_model': 'tapis.sale',
            'view_mode': 'form',
            'res_id': sale.id,
            'target': 'current',
        }

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tapis.crm.lead.code') or _('New')
        record = super().create(vals)
        record._trigger_communication('CRM_NEW_LEAD')
        return record
